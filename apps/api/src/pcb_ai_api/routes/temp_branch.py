"""Apply typed operations and emit a temporary KiCad schematic branch.

Guardrails: never writes production CAD. Uploaded schematics are compiled into
a system temp directory; the response carries branch-diff metadata and the
emitted ``.kicad_sch`` text. Human approval is still required before promoting
anything to production.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from pcb_ai_circuit_ir.models import Operation
from pcb_ai_transactions import TransactionError, compile_temp_branch

router = APIRouter(tags=["temp-branch"])


class TempBranchResponse(BaseModel):
    temp_schematic_name: str
    schematic_text: str
    branch_diff: dict = Field(default_factory=dict)
    production_mutation: bool = False
    human_approval_required: bool = True


@router.post("/temp-branch", response_model=TempBranchResponse)
async def create_temp_branch(
    file: UploadFile = File(..., description="Source KiCad .kicad_sch (read-only)"),
    operations_json: str = Form(
        ...,
        description="JSON array of typed Operation objects to apply on an IR copy",
    ),
    branch_name: str = Form(default="temp"),
) -> TempBranchResponse:
    """Ingest upload → apply operations → emit temp ``.kicad_sch`` (no production writes)."""
    try:
        raw_ops = json.loads(operations_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid operations_json: {exc}") from exc
    if not isinstance(raw_ops, list):
        raise HTTPException(status_code=400, detail="operations_json must be a JSON array")

    try:
        operations = [Operation.model_validate(item) for item in raw_ops]
    except Exception as exc:  # noqa: BLE001 — surface validation to client
        raise HTTPException(status_code=400, detail=f"Invalid operation: {exc}") from exc

    filename = file.filename or "upload.kicad_sch"
    if not filename.endswith(".kicad_sch"):
        filename = f"{filename}.kicad_sch"
    raw = await file.read()
    text = raw.decode("utf-8")

    with tempfile.TemporaryDirectory(prefix="pcb-ai-temp-branch-") as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "source" / filename
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
        dest_dir = tmp_path / "branch"
        try:
            result = compile_temp_branch(
                source,
                operations,
                dest_dir,
                branch_name=branch_name,
            )
        except TransactionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        emitted = result.path.read_text(encoding="utf-8")
        return TempBranchResponse(
            temp_schematic_name=result.path.name,
            schematic_text=emitted,
            branch_diff=result.branch_diff,
            production_mutation=False,
            human_approval_required=True,
        )
