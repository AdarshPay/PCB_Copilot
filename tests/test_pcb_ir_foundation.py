"""Minimal Phase B foundation tests (pcb-ir + PCB emit/ingest)."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_kicad_adapter import (
    ingest_pcb,
    schematic_design_to_board_skeleton,
    write_pcb,
)
from pcb_ai_layout import LayoutNotImplemented, LayoutPlanner, NullLayoutBackend
from pcb_ai_pcb_ir import Board, LAYOUT_OPERATION_TYPES
from pcb_ai_verification import parse_drc_report
from tests.conftest import load_golden


def test_board_ir_imports() -> None:
    board = Board(id="b1")
    assert board.id == "b1"
    assert "place_footprint" in LAYOUT_OPERATION_TYPES


def test_null_layout_backend_raises() -> None:
    design = load_golden("rc_divider.json")
    board = schematic_design_to_board_skeleton(design)
    planner = LayoutPlanner(NullLayoutBackend())
    try:
        planner.run(design, board)
        raise AssertionError("expected LayoutNotImplemented")
    except LayoutNotImplemented:
        pass


def test_schematic_to_board_skeleton_and_pcb_roundtrip(tmp_path: Path) -> None:
    design = load_golden("rc_divider.json")
    board = schematic_design_to_board_skeleton(design)
    assert len(board.footprints) == len(design.components)
    assert {n.name for n in board.nets} == {n.name for n in design.nets}
    assert all(not fp.placement.placed for fp in board.footprints)

    out = tmp_path / "rc_divider.kicad_pcb"
    write_pcb(board, out)
    assert out.is_file()
    loaded = ingest_pcb(out)
    assert {fp.reference for fp in loaded.footprints} == {
        fp.reference for fp in board.footprints
    }
    assert len(loaded.nets) >= len(board.nets)


def test_parse_drc_fixture_schema() -> None:
    report = {
        "violations": [
            {
                "type": "clearance",
                "severity": "error",
                "description": "Clearance violation between tracks",
                "items": [{"description": "seg1"}, {"description": "seg2"}],
            }
        ]
    }
    findings = parse_drc_report(report)
    assert len(findings) == 1
    assert findings[0].rule_id == "drc.clearance"
    assert findings[0].source == "kicad_drc"
