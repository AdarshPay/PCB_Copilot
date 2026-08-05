"""KiCad adapter public surface."""

from pcb_ai_kicad_adapter.emit import emit_schematic_ast, emit_schematic_text, write_schematic
from pcb_ai_kicad_adapter.normalize import ingest_schematic, normalize_to_circuit_ir
from pcb_ai_kicad_adapter.parser import dump_schematic_sexpr, parse_schematic_sexpr, serialize_sexpr
from pcb_ai_kicad_adapter.semantic import (
    collect_ast_uuids,
    semantic_diff,
    semantic_equal,
    semantic_fingerprint,
    uuid_equal,
    uuid_fingerprint,
)

__all__ = [
    "collect_ast_uuids",
    "dump_schematic_sexpr",
    "emit_schematic_ast",
    "emit_schematic_text",
    "ingest_schematic",
    "write_schematic",
    "normalize_to_circuit_ir",
    "parse_schematic_sexpr",
    "semantic_diff",
    "semantic_equal",
    "semantic_fingerprint",
    "serialize_sexpr",
    "uuid_equal",
    "uuid_fingerprint",
]
