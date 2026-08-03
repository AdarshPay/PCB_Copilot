"""KiCad adapter: lossless AST parse and Circuit IR normalization (stub)."""

from pcb_ai_kicad_adapter.parser import parse_schematic_sexpr
from pcb_ai_kicad_adapter.normalize import normalize_to_circuit_ir

__all__ = ["parse_schematic_sexpr", "normalize_to_circuit_ir"]
