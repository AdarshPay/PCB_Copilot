"""Mutation tests: one injected fault per rule, plus clean-fixture negatives."""

from __future__ import annotations

import pytest

from pcb_ai_verification import run_rules
from tests.conftest import load_golden
from tests.mutation.ir_mutators import (
    FIRST_PACK_RULE_IDS,
    mutate_duplicate_reference,
    mutate_missing_footprint,
    mutate_missing_open_drain_pullup,
    mutate_missing_pin,
    mutate_missing_power_source,
    mutate_output_conflict,
    mutate_reversed_polarity,
    mutate_undriven_input,
    mutate_voltage_domain_conflict,
)

CLEAN_GOLDENS = (
    "rc_divider.json",
    "i2c_sensor.json",
    "ldo_rail.json",
    "uart_bridge.json",
    "can_transceiver.json",
    "rs485_link.json",
    "esd_connector.json",
    "buck_regulator.json",
    "programming_header.json",
)


def _first_pack_ids(findings) -> set[str]:
    return {f.rule_id for f in findings if f.rule_id in FIRST_PACK_RULE_IDS}


@pytest.mark.parametrize("name", CLEAN_GOLDENS)
def test_clean_goldens_have_no_first_pack_findings(name: str) -> None:
    findings = run_rules(load_golden(name))
    assert _first_pack_ids(findings) == set()


@pytest.mark.parametrize(
    ("mutator", "expected_rule"),
    [
        (mutate_duplicate_reference, "struct.unique_references"),
        (mutate_missing_pin, "struct.pin_existence"),
        (mutate_missing_footprint, "struct.footprint_presence"),
        (mutate_output_conflict, "elec.output_conflict"),
        (mutate_undriven_input, "elec.undriven_input"),
        (mutate_missing_power_source, "elec.power_source"),
        (mutate_missing_open_drain_pullup, "elec.open_drain_pullup"),
        (mutate_voltage_domain_conflict, "elec.voltage_domain"),
        (mutate_reversed_polarity, "elec.polarity"),
    ],
    ids=[
        "unique_references",
        "pin_existence",
        "footprint_presence",
        "output_conflict",
        "undriven_input",
        "power_source",
        "open_drain_pullup",
        "voltage_domain",
        "polarity",
    ],
)
@pytest.mark.parametrize(
    "base",
    CLEAN_GOLDENS,
    ids=[
        "rc_divider",
        "i2c_sensor",
        "ldo_rail",
        "uart_bridge",
        "can_transceiver",
        "rs485_link",
        "esd_connector",
        "buck_regulator",
        "programming_header",
    ],
)
def test_single_fault_fires_expected_rule(mutator, expected_rule: str, base: str) -> None:
    clean = load_golden(base)
    assert _first_pack_ids(run_rules(clean)) == set()

    mutant = mutator(clean)
    fired = _first_pack_ids(run_rules(mutant))
    assert expected_rule in fired
    # High precision: exactly one first-pack rule for a single injected fault.
    assert fired == {expected_rule}


def test_output_conflict_golden_precision() -> None:
    """Dedicated conflict fixture should fire output_conflict without other first-pack noise."""
    findings = run_rules(load_golden("output_conflict.json"))
    fired = _first_pack_ids(findings)
    assert fired == {"elec.output_conflict"}
