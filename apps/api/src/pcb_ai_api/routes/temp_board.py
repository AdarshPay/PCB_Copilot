"""Compile a temporary KiCad board branch via Phase B layout.

Guardrails: never writes production CAD. Uploaded schematics are laid out into
an isolated temp directory; response carries PCB text + branch-diff metadata.
Human approval is required before promoting anything to production.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from pcb_ai_api.routes.proposals import get_decision_telemetry
from pcb_ai_circuit_ir.models import Design, Finding, Operation
from pcb_ai_pcb_ir.models import Board
from pcb_ai_transactions import TransactionError, compile_temp_board_branch

router = APIRouter(tags=["temp-board"])


class TempBoardResponse(BaseModel):
    proposal_id: str
    temp_board_name: str
    pcb_text: str
    board: Board
    operations: list[Operation] = Field(default_factory=list)
    layout_findings: list[Finding] = Field(default_factory=list)
    unrouted_nets: list[str] = Field(default_factory=list)
    branch_diff: dict = Field(default_factory=dict)
    production_mutation: bool = False
    human_approval_required: bool = True


class TempBoardFromDesignRequest(BaseModel):
    design: Design
    pcb_name: str = "board-copilot.kicad_pcb"
    register_proposal: bool = True


def _temp_board_response(
    design: Design,
    *,
    pcb_name: str,
    register_proposal: bool,
) -> TempBoardResponse:
    proposal_id = str(uuid4())
    with tempfile.TemporaryDirectory(prefix="pcb-ai-temp-board-") as tmp:
        dest_dir = Path(tmp) / "branch"
        try:
            result = compile_temp_board_branch(
                design,
                dest_dir,
                pcb_name=pcb_name,
                register_proposal=register_proposal,
                telemetry=get_decision_telemetry() if register_proposal else None,
                proposal_id=proposal_id,
            )
        except TransactionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Temp board failed: {exc}") from exc

        return TempBoardResponse(
            proposal_id=result.proposal_id,
            temp_board_name=result.path.name,
            pcb_text=result.path.read_text(encoding="utf-8"),
            board=result.board,
            operations=list(result.board.operations),
            layout_findings=list(result.board.findings),
            unrouted_nets=list(result.board.unrouted_nets),
            branch_diff=result.branch_diff,
            production_mutation=False,
            human_approval_required=True,
        )


@router.post("/temp-board", response_model=TempBoardResponse)
async def create_temp_board(
    file: UploadFile = File(..., description="Source KiCad .kicad_sch (read-only)"),
    pcb_name: str = Form(default="board-copilot.kicad_pcb"),
    register_proposal: bool = Form(default=True),
) -> TempBoardResponse:
    """Ingest upload → layout → emit temp ``.kicad_pcb`` (no production writes)."""
    filename = file.filename or "upload.kicad_sch"
    raw = await file.read()
    text = raw.decode("utf-8")
    from pcb_ai_kicad_adapter import ingest_schematic

    stem = filename.removesuffix(".kicad_sch")
    design = ingest_schematic(text, design_id=f"kicad.{stem}")
    return _temp_board_response(
        design,
        pcb_name=pcb_name,
        register_proposal=register_proposal,
    )


@router.post("/temp-board/from-design", response_model=TempBoardResponse)
def create_temp_board_from_design(body: TempBoardFromDesignRequest) -> TempBoardResponse:
    return _temp_board_response(
        body.design,
        pcb_name=body.pcb_name,
        register_proposal=body.register_proposal,
    )
