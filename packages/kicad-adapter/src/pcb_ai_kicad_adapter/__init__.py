"""KiCad adapter public surface."""

from pcb_ai_kicad_adapter.emit import emit_schematic_ast, emit_schematic_text
from pcb_ai_kicad_adapter.normalize import ingest_schematic, normalize_to_circuit_ir
from pcb_ai_kicad_adapter.parser import dump_schematic_sexpr, parse_schematic_sexpr, serialize_sexpr
from pcb_ai_kicad_adapter.semantic import semantic_diff, semantic_equal, semantic_fingerprint

__all__ = [
    "dump_schematic_sexpr",
    "emit_schematic_ast",
    "emit_schematic_text",
    "ingest_schematic",
    "normalize_to_circuit_ir",
    "parse_schematic_sexpr",
    "semantic_diff",
    "semantic_equal",
    "semantic_fingerprint",
    "serialize_sexpr",
]
