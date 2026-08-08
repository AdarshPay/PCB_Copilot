"""Transaction compiler — reversible Circuit IR edits on Design copies only.

Guardrails: never mutates production CAD. Use ``apply_operations`` /
``export_branch_diff`` for IR review, or ``compile_temp_branch`` to emit a
temporary ``.kicad_sch`` under a dest directory (human approval still required
before any production write).

Phase B board branches: ``compile_temp_board_branch`` (requires ``pcb-ai-layout``).
"""

from __future__ import annotations

from typing import Any

from pcb_ai_transactions.compiler import (
    SUPPORTED_OPERATION_TYPES,
    TransactionCompiler,
    TransactionError,
    apply_operations,
    export_branch_diff,
    semantic_diff,
)
from pcb_ai_transactions.temp_branch import TempBranchResult, compile_temp_branch, emit_design_to_temp

__all__ = [
    "SUPPORTED_OPERATION_TYPES",
    "TempBoardBranchResult",
    "TempBranchResult",
    "TransactionCompiler",
    "TransactionError",
    "apply_operations",
    "board_semantic_diff",
    "compile_temp_board_branch",
    "compile_temp_branch",
    "emit_design_to_temp",
    "export_branch_diff",
    "semantic_diff",
]


def __getattr__(name: str) -> Any:
    """Lazy-load board-branch helpers so Phase A installs stay layout-optional."""
    if name in {"TempBoardBranchResult", "board_semantic_diff", "compile_temp_board_branch"}:
        from pcb_ai_transactions import temp_board

        return getattr(temp_board, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
