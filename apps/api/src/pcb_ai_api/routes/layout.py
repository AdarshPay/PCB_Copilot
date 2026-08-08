"""Layout a verified schematic into a temporary KiCad board (Phase B).

Guardrails: never writes production CAD. Uploaded schematics / IR designs are
laid out into an isolated temp directory; the response carries PCB text,
findings, and a ``proposal_id`` for approve/reject telemetry. Human approval
is required before promoting anything to production.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from pcb_ai_api.routes.proposals import get_decision_telemetry
from pcb_ai_circuit_ir.models import Design, Finding, Operation
from pcb_ai_layout import run_layout_job
from pcb_ai_pcb_ir.models import Board

router = APIRouter(tags=["layout"])


class LayoutResponse(BaseModel):
    job_id: str
    proposal_id: str
    design_id: str
    pcb_name: str
    pcb_text: str
    board: Board
    operations: list[Operation] = Field(default_factory=list)
    layout_findings: list[Finding] = Field(default_factory=list)
    rule_findings: list[Finding] = Field(default_factory=list)
    unrouted_nets: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    production_mutation: bool = False
    human_approval_required: bool = True


class LayoutFromDesignRequest(BaseModel):
    design: Design
    pcb_name: str = "layout.kicad_pcb"
    register_proposal: bool = True


def _run_layout_response(
    design: Design,
    *,
    pcb_name: str,
    register_proposal: bool,
) -> LayoutResponse:
    job_id = str(uuid4())
    with tempfile.TemporaryDirectory(prefix="pcb-ai-layout-") as tmp:
        dest = Path(tmp) / job_id
        try:
            result = run_layout_job(
                design,
                dest,
                pcb_name=pcb_name,
                register_proposal=register_proposal,
                telemetry=get_decision_telemetry() if register_proposal else None,
                proposal_id=job_id,
            )
        except Exception as exc:  # noqa: BLE001 — surface layout failures to client
            raise HTTPException(status_code=400, detail=f"Layout failed: {exc}") from exc

        pcb_text = result.pcb_path.read_text(encoding="utf-8")
        return LayoutResponse(
            job_id=job_id,
            proposal_id=result.proposal_id,
            design_id=design.id,
            pcb_name=result.pcb_path.name,
            pcb_text=pcb_text,
            board=result.board,
            operations=list(result.board.operations),
            layout_findings=list(result.board.findings),
            rule_findings=list(result.rule_findings),
            unrouted_nets=list(result.unrouted_nets),
            metadata=dict(result.metadata),
            production_mutation=False,
            human_approval_required=True,
        )


@router.post("/layout", response_model=LayoutResponse)
async def create_layout(
    file: UploadFile | None = File(
        default=None,
        description="KiCad .kicad_sch upload (read-only)",
    ),
    design_json: str | None = Form(
        default=None,
        description="Optional Circuit IR Design JSON when no schematic file is uploaded",
    ),
    pcb_name: str = Form(default="layout.kicad_pcb"),
    register_proposal: bool = Form(default=True),
) -> LayoutResponse:
    """Place/route into a temp ``.kicad_pcb`` (multipart sch or Design JSON)."""
    if file is None and not design_json:
        raise HTTPException(
            status_code=400,
            detail="Provide either a schematic file or design_json form field",
        )

    if file is not None:
        filename = file.filename or "upload.kicad_sch"
        raw = await file.read()
        text = raw.decode("utf-8")
        if filename.endswith(".json") or (design_json is None and text.lstrip().startswith("{")):
            try:
                design = Design.model_validate(json.loads(text))
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"Invalid design JSON: {exc}") from exc
        else:
            from pcb_ai_kicad_adapter import ingest_schematic

            stem = filename.removesuffix(".kicad_sch")
            design = ingest_schematic(text, design_id=f"kicad.{stem}")
    else:
        assert design_json is not None
        try:
            design = Design.model_validate(json.loads(design_json))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid design_json: {exc}") from exc

    return _run_layout_response(
        design,
        pcb_name=pcb_name,
        register_proposal=register_proposal,
    )


@router.post("/layout/from-design", response_model=LayoutResponse)
def create_layout_from_design(body: LayoutFromDesignRequest) -> LayoutResponse:
    """JSON-body convenience for golden IR / agent callers."""
    return _run_layout_response(
        body.design,
        pcb_name=body.pcb_name,
        register_proposal=body.register_proposal,
    )
