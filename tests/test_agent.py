"""Planner + deterministic remediation tests (Phase A Day 60)."""

from __future__ import annotations

import pytest

from pcb_ai_agent import (
    Planner,
    PlannerDisabled,
    SUPPORTED_RULE_IDS,
    map_findings_to_operations,
)
from pcb_ai_transactions import apply_operations, export_branch_diff
from pcb_ai_verification import run_rules
from tests.conftest import load_golden
from tests.mutation.ir_mutators import (
    mutate_duplicate_reference,
    mutate_missing_footprint,
    mutate_missing_open_drain_pullup,
    mutate_missing_pin,
    mutate_missing_power_source,
    mutate_output_conflict,
    mutate_reversed_polarity,
    mutate_undriven_input,
)

BASE = "i2c_sensor.json"


def test_planner_disabled_by_default() -> None:
    planner = Planner()
    design = load_golden(BASE)
    with pytest.raises(PlannerDisabled):
        planner.propose(design, [])


def test_planner_enabled_returns_typed_ops_for_pullup() -> None:
    design = mutate_missing_open_drain_pullup(load_golden(BASE))
    findings = [f for f in run_rules(design) if f.rule_id == "elec.open_drain_pullup"]
    assert findings
    ops = Planner(enabled=True).propose(design, findings)
    assert ops
    assert all(op.type for op in ops)
    assert {op.type for op in ops} >= {"add_component", "add_endpoint"}


@pytest.mark.parametrize(
    ("mutator", "rule_id"),
    [
        (mutate_missing_open_drain_pullup, "elec.open_drain_pullup"),
        (mutate_missing_footprint, "struct.footprint_presence"),
        (mutate_undriven_input, "elec.undriven_input"),
        (mutate_missing_power_source, "elec.power_source"),
        (mutate_output_conflict, "elec.output_conflict"),
        (mutate_reversed_polarity, "elec.polarity"),
        (mutate_duplicate_reference, "struct.unique_references"),
        (mutate_missing_pin, "struct.pin_existence"),
    ],
    ids=[
        "open_drain_pullup",
        "footprint_presence",
        "undriven_input",
        "power_source",
        "output_conflict",
        "polarity",
        "unique_references",
        "pin_existence",
    ],
)
def test_propose_apply_clears_target_rule(mutator, rule_id: str) -> None:
    assert rule_id in SUPPORTED_RULE_IDS
    clean = load_golden(BASE)
    mutant = mutator(clean)
    before_findings = run_rules(mutant)
    target = [f for f in before_findings if f.rule_id == rule_id]
    assert target, f"expected {rule_id} on mutant"

    ops = map_findings_to_operations(mutant, target)
    assert ops, f"expected remediation ops for {rule_id}"

    after = apply_operations(mutant, ops)
    # Original IR must stay untouched (apply is copy-only).
    assert run_rules(mutant)  # still has findings
    assert any(f.rule_id == rule_id for f in run_rules(mutant))

    after_findings = run_rules(after)
    assert not any(f.rule_id == rule_id for f in after_findings), (
        f"{rule_id} still present after remediation: "
        f"{[f.rule_id for f in after_findings]}"
    )

    diff = export_branch_diff(mutant, after, operations=ops, branch_name="temp")
    assert diff["production_mutation"] is False
    assert diff["branch"] == "temp"
    assert diff["operation_count"] == len(ops)


def test_unsupported_rule_yields_no_ops() -> None:
    design = load_golden(BASE)
    from pcb_ai_circuit_ir.models import Finding, Severity

    finding = Finding(
        rule_id="elec.voltage_domain",
        severity=Severity.ERROR,
        objects=["NET_X", "3V3", "5V"],
        explanation="unsupported in MVP mapper",
    )
    assert map_findings_to_operations(design, [finding]) == []
