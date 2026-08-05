"""Deterministic rule engine tests against golden fixtures."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import (
    Component,
    ElectricalRole,
    Endpoint,
    FunctionalClass,
    Net,
    NetClass,
    Pin,
)
from pcb_ai_verification import RULE_PACK_V0, run_rules
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


def test_rule_pack_includes_first_pack_checks() -> None:
    ids = {rule_id for rule_id, _ in RULE_PACK_V0}
    assert ids >= {
        "struct.unique_references",
        "struct.pin_existence",
        "struct.footprint_presence",
        "elec.output_conflict",
        "elec.undriven_input",
        "elec.power_source",
        "elec.open_drain_pullup",
        "elec.voltage_domain",
        "elec.polarity",
    }


def test_footprint_presence_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components.append(
        Component(
            reference="U6",
            value="MCU",
            functional_class=FunctionalClass.MCU,
            footprint_ref=None,
            pins=[Pin(number="1", name="NC", electrical_role=ElectricalRole.UNSPECIFIED)],
        )
    )
    findings = run_rules(design)
    assert any(f.rule_id == "struct.footprint_presence" for f in findings)


def test_passive_without_footprint_is_exempt() -> None:
    design = load_golden("rc_divider.json")
    design.components[0].footprint_ref = None
    findings = run_rules(design)
    assert not any(f.rule_id == "struct.footprint_presence" for f in findings)


def test_undriven_input_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components.append(
        Component(
            reference="U9",
            value="SENSOR",
            functional_class=FunctionalClass.SENSOR,
            footprint_ref="Package_TO_SOT_SMD:SOT-23",
            pins=[Pin(number="1", name="RESET", electrical_role=ElectricalRole.RESET)],
        )
    )
    findings = run_rules(design)
    assert any(f.rule_id == "elec.undriven_input" for f in findings)


def test_power_source_warning_on_signal_net() -> None:
    design = load_golden("rc_divider.json")
    design.components.append(
        Component(
            reference="U8",
            value="LOAD",
            functional_class=FunctionalClass.OTHER,
            pins=[Pin(number="1", name="VDD", electrical_role=ElectricalRole.POWER_IN)],
        )
    )
    design.nets.append(
        Net(
            name="FLOAT_VDD",
            net_class=NetClass.SIGNAL,
            endpoints=[Endpoint(component_ref="U8", pin_number="1")],
        )
    )
    findings = run_rules(design)
    assert any(f.rule_id == "elec.power_source" for f in findings)


def test_open_drain_pullup_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components.append(
        Component(
            reference="U7",
            value="OD",
            functional_class=FunctionalClass.OTHER,
            pins=[Pin(number="1", name="OD", electrical_role=ElectricalRole.OPEN_DRAIN)],
        )
    )
    design.nets.append(
        Net(
            name="OD_BUS",
            net_class=NetClass.BUS,
            endpoints=[Endpoint(component_ref="U7", pin_number="1")],
        )
    )
    findings = run_rules(design)
    assert any(f.rule_id == "elec.open_drain_pullup" for f in findings)


def test_i2c_sensor_has_pullups() -> None:
    design = load_golden("i2c_sensor.json")
    findings = run_rules(design)
    assert not any(f.rule_id == "elec.open_drain_pullup" for f in findings)


def test_voltage_domain_conflict_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components[0].pins[1].voltage_domain = "3V3"
    design.components[1].pins[0].voltage_domain = "5V"
    findings = run_rules(design)
    assert any(f.rule_id == "elec.voltage_domain" for f in findings)


def test_polarity_reversed_detected() -> None:
    design = load_golden("rc_divider.json")
    design.components.append(
        Component(
            reference="C1",
            value="10uF",
            functional_class=FunctionalClass.PASSIVE,
            pins=[
                Pin(number="1", name="+", electrical_role=ElectricalRole.PASSIVE),
                Pin(number="2", name="-", electrical_role=ElectricalRole.PASSIVE),
            ],
            attributes={"polarized": True, "positive_pin": "1", "negative_pin": "2"},
        )
    )
    # Reversed across VIN (power) and GND.
    for net in design.nets:
        if net.name == "GND":
            net.endpoints.append(Endpoint(component_ref="C1", pin_number="1"))
        if net.name == "VIN":
            net.endpoints.append(Endpoint(component_ref="C1", pin_number="2"))
    findings = run_rules(design)
    assert any(f.rule_id == "elec.polarity" for f in findings)
