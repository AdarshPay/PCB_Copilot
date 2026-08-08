"""Minimal Phase B foundation tests (pcb-ir + PCB emit/ingest + grid layout)."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_kicad_adapter import (
    ingest_pcb,
    schematic_design_to_board_skeleton,
    write_pcb,
)
from pcb_ai_layout import (
    GridLayoutBackend,
    LayoutNotImplemented,
    LayoutPlanner,
    NullLayoutBackend,
    load_design_from_source,
    run_layout_job,
)
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
    except LayoutNotImplemented:
        pass
    else:
        raise AssertionError("expected LayoutNotImplemented")


def test_layout_planner_defaults_to_grid() -> None:
    design = load_golden("rc_divider.json")
    skeleton = schematic_design_to_board_skeleton(design)
    board = LayoutPlanner().run(design, skeleton)
    assert isinstance(LayoutPlanner().backend, GridLayoutBackend)
    assert all(fp.placement.placed for fp in board.footprints)
    assert board.tracks
    assert board.attributes.get("layout_backend") == "grid_mvp"


def test_grid_layout_job_emits_temp_pcb(tmp_path: Path) -> None:
    design = load_golden("rc_divider.json")
    result = run_layout_job(design, tmp_path, register_proposal=False)
    assert result.pcb_path.is_file()
    assert result.pcb_path.read_text(encoding="utf-8").startswith("(kicad_pcb")
    assert result.metadata["placed"] == len(design.components)
    assert result.metadata["production_mutation"] is False
    assert result.summary()["human_approval_required"] is True
    loaded = ingest_pcb(result.pcb_path)
    assert {fp.reference for fp in loaded.footprints} == {
        c.reference for c in design.components
    }


def test_load_design_from_source_json() -> None:
    src = Path(__file__).resolve().parent / "fixtures" / "golden" / "rc_divider.json"
    design = load_design_from_source(src)
    assert design.id
    assert design.components


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
