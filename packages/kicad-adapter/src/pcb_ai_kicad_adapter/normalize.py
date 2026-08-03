"""Normalize KiCad AST into Circuit IR.

Full symbol/pin/net extraction lands in sprint days 3–5. For now this accepts
an already-normalized Design or raises for unsupported AST shapes.
"""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design
from pcb_ai_kicad_adapter.parser import SExprNode


class NormalizationError(ValueError):
    pass


def normalize_to_circuit_ir(ast: SExprNode | Design, *, design_id: str | None = None) -> Design:
    """Convert a parsed schematic AST into a typed Design.

    If a Design is passed through (e.g. golden fixtures), it is returned as-is.
    """
    if isinstance(ast, Design):
        return ast
    if ast.head != "kicad_sch":
        raise NormalizationError(f"Expected kicad_sch root, got {ast.head!r}")
    raise NormalizationError(
        "Full KiCad-to-IR normalization is not implemented yet "
        f"(design_id={design_id!r}). Use Circuit IR fixtures until days 3–5."
    )
