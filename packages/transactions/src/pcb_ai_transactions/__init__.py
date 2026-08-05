"""Transaction compiler — reversible Circuit IR edits on Design copies only.

Guardrails: never mutates production CAD. Use ``apply_operations`` /
``export_branch_diff`` for IR review, or ``compile_temp_branch`` to emit a
temporary ``.kicad_sch`` under a dest directory (human approval still required
before any production write).
"""

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
    "TempBranchResult",
    "TransactionCompiler",
    "TransactionError",
    "apply_operations",
    "compile_temp_branch",
    "emit_design_to_temp",
    "export_branch_diff",
    "semantic_diff",
]
