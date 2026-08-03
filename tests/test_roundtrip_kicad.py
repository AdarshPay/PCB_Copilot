"""Round-trip and ingest tests for KiCad schematics."""

from __future__ import annotations

from pathlib import Path

import pytest

from pcb_ai_kicad_adapter import (
    dump_schematic_sexpr,
    emit_schematic_text,
    ingest_schematic,
    normalize_to_circuit_ir,
    parse_schematic_sexpr,
    semantic_equal,
)
from pcb_ai_kicad_adapter.parser import SExprNode
from pcb_ai_verification import run_rules

KICAD_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kicad"
RC_DIVIDER = KICAD_FIXTURES / "rc_divider.kicad_sch"


def _ast_equal(a: SExprNode, b: SExprNode) -> bool:
    if a.is_atom or b.is_atom:
        return a.is_atom and b.is_atom and a.atom == b.atom
    if a.head != b.head or len(a.children) != len(b.children):
        return False
    return all(
        isinstance(x, SExprNode) and isinstance(y, SExprNode) and _ast_equal(x, y)
        for x, y in zip(a.children, b.children, strict=True)
    )


def test_rc_divider_fixture_exists() -> None:
    assert RC_DIVIDER.is_file()


def test_parse_rc_divider_ast() -> None:
    ast = parse_schematic_sexpr(RC_DIVIDER)
    assert ast.head == "kicad_sch"
    assert ast.find("version") is not None
    assert len(ast.find_all("symbol")) >= 3  # R1, R2, GND (+ nested ignored at root)
    assert ast.find("lib_symbols") is not None


def test_ast_serialize_roundtrip_no_semantic_change() -> None:
    original = parse_schematic_sexpr(RC_DIVIDER)
    text = dump_schematic_sexpr(original)
    again = parse_schematic_sexpr(text)
    assert _ast_equal(original, again)


def test_normalize_rc_divider_components_and_nets() -> None:
    design = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    refs = {c.reference for c in design.components}
    assert {"R1", "R2", "#PWR01"} <= refs

    r1 = next(c for c in design.components if c.reference == "R1")
    assert r1.value == "10k"
    assert r1.symbol_ref == "Device:R"
    assert r1.footprint_ref == "Resistor_SMD:R_0603_1608Metric"
    assert {p.number for p in r1.pins} == {"1", "2"}

    nets = {n.name: n for n in design.nets}
    assert "VIN" in nets
    assert "MID" in nets
    assert "GND" in nets

    mid_eps = {(e.component_ref, e.pin_number) for e in nets["MID"].endpoints}
    assert mid_eps == {("R1", "2"), ("R2", "1")}

    vin_eps = {(e.component_ref, e.pin_number) for e in nets["VIN"].endpoints}
    assert ("R1", "1") in vin_eps

    gnd_eps = {(e.component_ref, e.pin_number) for e in nets["GND"].endpoints}
    assert ("R2", "2") in gnd_eps
    assert ("#PWR01", "1") in gnd_eps


def test_normalize_then_emit_then_normalize_semantic_equal() -> None:
    first = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    emitted = emit_schematic_text(first)
    second = normalize_to_circuit_ir(
        parse_schematic_sexpr(emitted),
        design_id="fixture.rc_divider.kicad",
    )
    assert semantic_equal(first, second)


def test_ingest_runs_deterministic_rules() -> None:
    design = ingest_schematic(RC_DIVIDER)
    findings = run_rules(design)
    # Structural rules should pass on a well-formed divider.
    assert not any(f.rule_id == "struct.unique_references" for f in findings)
    assert not any(f.rule_id == "struct.pin_existence" for f in findings)


def test_cli_ingest(tmp_path: Path) -> None:
    from pcb_ai_kicad_adapter.__main__ import main

    out = tmp_path / "design.json"
    code = main([str(RC_DIVIDER), "-o", str(out), "--rules"])
    assert code == 0
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "R1" in text
    assert "findings" in text
