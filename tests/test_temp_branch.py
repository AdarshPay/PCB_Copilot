"""Temp-branch KiCad emit: apply ops to IR and write a temporary .kicad_sch."""

from __future__ import annotations

from pathlib import Path

import pytest

from pcb_ai_circuit_ir.models import Operation
from pcb_ai_kicad_adapter import ingest_schematic, parse_schematic_sexpr
from pcb_ai_transactions import TransactionError, compile_temp_branch, emit_design_to_temp

KICAD_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kicad"
RC_DIVIDER = KICAD_FIXTURES / "rc_divider.kicad_sch"


def test_compile_temp_branch_leaves_production_unchanged(tmp_path: Path) -> None:
    assert RC_DIVIDER.is_file()
    before_bytes = RC_DIVIDER.read_bytes()
    before_mtime = RC_DIVIDER.stat().st_mtime_ns

    ops = [
        Operation(
            type="set_component_value",
            target="R1",
            payload={"value": "20k"},
            risk_tier="low",
            confidence=1.0,
        )
    ]
    dest_dir = tmp_path / "branch"
    result = compile_temp_branch(RC_DIVIDER, ops, dest_dir, branch_name="review")

    assert result.path.is_file()
    assert result.path.parent == dest_dir.resolve()
    assert result.path.name == RC_DIVIDER.name
    assert result.path.resolve() != RC_DIVIDER.resolve()
    assert RC_DIVIDER.read_bytes() == before_bytes
    assert RC_DIVIDER.stat().st_mtime_ns == before_mtime

    ast = parse_schematic_sexpr(result.path)
    assert ast.head == "kicad_sch"
    reingested = ingest_schematic(result.path)
    r1 = next(c for c in reingested.components if c.reference == "R1")
    assert r1.value == "20k"

    assert result.branch_diff["production_mutation"] is False
    assert result.branch_diff["human_approval_required"] is True
    assert result.branch_diff["branch"] == "review"
    assert result.branch_diff["operation_count"] == 1
    assert "R1" in result.branch_diff["changed_components"]
    assert result.production_mutation is False


def test_compile_temp_branch_refuses_production_dest(tmp_path: Path) -> None:
    ops = [Operation(type="noop", target="", payload={})]
    with pytest.raises(TransactionError, match="production"):
        compile_temp_branch(RC_DIVIDER, ops, RC_DIVIDER.parent, dest_name=RC_DIVIDER.name)


def test_emit_design_to_temp_writes_parseable_file(tmp_path: Path) -> None:
    design = ingest_schematic(RC_DIVIDER)
    dest = tmp_path / "out.kicad_sch"
    path = emit_design_to_temp(design, dest, source_sch=RC_DIVIDER)
    assert path == dest.resolve()
    assert parse_schematic_sexpr(path).head == "kicad_sch"
    assert RC_DIVIDER.is_file()
