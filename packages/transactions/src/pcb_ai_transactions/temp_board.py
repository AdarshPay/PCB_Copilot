"""Compile layout onto a temporary KiCad board branch (Phase B).

Import from the package root::

    from pcb_ai_transactions import compile_temp_board_branch

Requires ``pcb-ai-layout`` (and ``pcb-ai-pcb-ir``) installed. Never writes
production CAD; refuse overwrite of ``source_pcb``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pcb_ai_circuit_ir.models import Design, Operation
from pcb_ai_kicad_adapter import write_pcb
from pcb_ai_pcb_ir.models import Board
from pcb_ai_transactions.compiler import TransactionError


@dataclass(frozen=True)
class TempBoardBranchResult:
    path: Path
    board: Board
    design: Design
    branch_diff: dict[str, Any]
    proposal_id: str

    @property
    def production_mutation(self) -> bool:
        return False


def board_semantic_diff(before: Board, after: Board) -> dict[str, Any]:
    return {
        "footprints_before": len(before.footprints),
        "footprints_after": len(after.footprints),
        "placed_before": sum(1 for f in before.footprints if f.placement.placed),
        "placed_after": sum(1 for f in after.footprints if f.placement.placed),
        "tracks_before": len(before.tracks),
        "tracks_after": len(after.tracks),
        "vias_before": len(before.vias),
        "vias_after": len(after.vias),
        "unrouted_after": list(after.unrouted_nets),
        "operations": len(after.operations),
    }


def compile_temp_board_branch(
    design: Design,
    dest_dir: Path | str,
    *,
    operations: list[Operation] | None = None,
    pcb_name: str = "board.kicad_pcb",
    source_pcb: Path | str | None = None,
    register_proposal: bool = True,
    telemetry: Any | None = None,
    proposal_id: str | None = None,
) -> TempBoardBranchResult:
    """Layout ``design`` into a temp ``.kicad_pcb`` under ``dest_dir``.

    Refuses to overwrite ``source_pcb``. Human approval required before promote.
    """
    from pcb_ai_layout.service import run_layout_job

    out_dir = Path(dest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = (out_dir / pcb_name).resolve()

    if source_pcb is not None:
        source = Path(source_pcb).resolve()
        if dest == source:
            raise TransactionError(
                "Refusing to write temp board branch onto the production PCB path"
            )

    result = run_layout_job(
        design,
        out_dir,
        pcb_name=pcb_name,
        register_proposal=register_proposal,
        telemetry=telemetry,
        proposal_id=proposal_id,
    )
    if operations:
        result.board.operations.extend(operations)
        write_pcb(result.board, dest)

    empty = Board(id="empty")
    diff = board_semantic_diff(empty, result.board)
    diff["production_mutation"] = False
    diff["artifact"] = str(dest)
    diff["proposal_id"] = result.proposal_id
    if dest.is_file():
        diff["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()

    return TempBoardBranchResult(
        path=dest,
        board=result.board,
        design=design,
        branch_diff=diff,
        proposal_id=result.proposal_id,
    )
