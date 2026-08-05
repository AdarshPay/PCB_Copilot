"""Transaction compiler — reversible Circuit IR edits on Design copies only.

Guardrails: never mutates production CAD. Use ``apply_operations`` /
``export_branch_diff`` for temp-branch style review of typed Operations.
"""

from pcb_ai_transactions.compiler import (
    SUPPORTED_OPERATION_TYPES,
    TransactionCompiler,
    TransactionError,
    apply_operations,
    export_branch_diff,
    semantic_diff,
)

__all__ = [
    "SUPPORTED_OPERATION_TYPES",
    "TransactionCompiler",
    "TransactionError",
    "apply_operations",
    "export_branch_diff",
    "semantic_diff",
]
