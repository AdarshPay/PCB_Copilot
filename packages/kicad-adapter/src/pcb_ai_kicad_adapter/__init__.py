"""KiCad adapter public surface."""

from pcb_ai_kicad_adapter.board_bridge import schematic_design_to_board_skeleton
from pcb_ai_kicad_adapter.emit import emit_schematic_ast, emit_schematic_text, write_schematic
from pcb_ai_kicad_adapter.normalize import ingest_schematic, normalize_to_circuit_ir
from pcb_ai_kicad_adapter.parser import dump_schematic_sexpr, parse_schematic_sexpr, serialize_sexpr
from pcb_ai_kicad_adapter.pcb import (
    emit_pcb_ast,
    emit_pcb_text,
    ingest_pcb,
    normalize_pcb_to_board,
    write_pcb,
)
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
    "emit_pcb_ast",
    "emit_pcb_text",
    "emit_schematic_ast",
    "emit_schematic_text",
    "ingest_pcb",
    "ingest_schematic",
    "normalize_pcb_to_board",
    "write_pcb",
    "write_schematic",
    "normalize_to_circuit_ir",
    "parse_schematic_sexpr",
    "schematic_design_to_board_skeleton",
    "semantic_diff",
    "semantic_equal",
    "semantic_fingerprint",
    "serialize_sexpr",
    "uuid_equal",
    "uuid_fingerprint",
]
