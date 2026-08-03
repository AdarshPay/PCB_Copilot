"""Deterministic rule engine tests against golden fixtures."""

from __future__ import annotations

from pcb_ai_verification import run_rules
from tests.conftest import load_golden


def test_rc_divider_has_no_errors() -> None:
    design = load_golden("rc_divider.json")
    findings = run_rules(design)
    errors = [f for f in findings if f.severity.value in {"error", "critical"}]
    assert errors == []


def test_i2c_sensor_has_no_structural_errors() -> None:
    design = load_golden("i2c_sensor.json")
    findings = run_rules(design)
    structural = [f for f in findings if f.rule_id.startswith("struct.")]
    assert structural == []


def test_output_conflict_detected() -> None:
    design = load_golden("output_conflict.json")
    findings = run_rules(design)
    rules = {f.rule_id for f in findings}
    assert "elec.output_conflict" in rules


def test_duplicate_reference_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components[1].reference = design.components[0].reference
    findings = run_rules(design)
    assert any(f.rule_id == "struct.unique_references" for f in findings)
