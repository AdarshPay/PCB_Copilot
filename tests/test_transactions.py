"""Transaction compiler tests for typed IR operations (Phase A Day 60)."""

from __future__ import annotations

import pytest

from pcb_ai_circuit_ir.models import Operation
from pcb_ai_transactions import (
    SUPPORTED_OPERATION_TYPES,
    TransactionCompiler,
    TransactionError,
    apply_operations,
    export_branch_diff,
    semantic_diff,
)
from tests.conftest import load_golden


def test_set_component_value_and_rollback_metadata() -> None:
    design = load_golden("rc_divider.json")
    op = Operation(
        type="set_component_value",
        target="R1",
        payload={"value": "20k"},
        risk_tier="low",
        confidence=1.0,
    )
    after = apply_operations(design, [op])
    assert design.components[0].value == "10k"
    r1 = next(c for c in after.components if c.reference == "R1")
    assert r1.value == "20k"
    assert op.rollback.get("previous_value") == "10k"


def test_add_component_and_endpoint_round_trip() -> None:
    design = load_golden("rc_divider.json")
    ops = [
        Operation(
            type="add_component",
            target="R_PU_1",
            payload={
                "component": {
                    "reference": "R_PU_1",
                    "value": "4.7k",
                    "functional_class": "passive",
                    "pins": [
                        {"number": "1", "name": "1", "electrical_role": "passive"},
                        {"number": "2", "name": "2", "electrical_role": "passive"},
                    ],
                }
            },
        ),
        Operation(
            type="add_endpoint",
            target="VIN",
            payload={"component_ref": "R_PU_1", "pin_number": "1"},
        ),
        Operation(
            type="add_endpoint",
            target="MID",
            payload={"component_ref": "R_PU_1", "pin_number": "2"},
        ),
    ]
    after = TransactionCompiler().compile(design, ops)
    assert any(c.reference == "R_PU_1" for c in after.components)
    vin = next(n for n in after.nets if n.name == "VIN")
    assert any(ep.component_ref == "R_PU_1" for ep in vin.endpoints)
    diff = semantic_diff(design, after)
    assert "R_PU_1" in diff["added_components"]
    assert "VIN" in diff["changed_nets"] or "MID" in diff["changed_nets"]


def test_set_footprint_and_net_class() -> None:
    design = load_golden("i2c_sensor.json")
    ops = [
        Operation(
            type="set_footprint_ref",
            target="U1",
            payload={"footprint_ref": "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm"},
        ),
        Operation(
            type="set_net_class",
            target="I2C_SDA",
            payload={"net_class": "signal"},
        ),
    ]
    after = apply_operations(design, ops)
    u1 = next(c for c in after.components if c.reference == "U1")
    assert u1.footprint_ref == "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm"
    assert ops[0].rollback.get("footprint_ref")
    sda = next(n for n in after.nets if n.name == "I2C_SDA")
    assert sda.net_class.value == "signal"


def test_remove_endpoint_unknown_raises() -> None:
    design = load_golden("rc_divider.json")
    op = Operation(
        type="remove_endpoint",
        target="VIN",
        payload={"component_ref": "NOPE", "pin_number": "1"},
    )
    with pytest.raises(TransactionError):
        apply_operations(design, [op])


def test_unsupported_op_type_raises() -> None:
    design = load_golden("rc_divider.json")
    with pytest.raises(TransactionError, match="Unsupported"):
        apply_operations(
            design,
            [Operation(type="mutate_kicad_file", target="x", payload={})],
        )


def test_export_branch_diff_flags_no_production_mutation() -> None:
    design = load_golden("rc_divider.json")
    ops = [
        Operation(
            type="set_component_value",
            target="R2",
            payload={"value": "4.7k"},
        )
    ]
    after = apply_operations(design, ops)
    summary = export_branch_diff(design, after, operations=ops)
    assert summary["production_mutation"] is False
    assert summary["operation_count"] == 1
    assert "R2" in summary["changed_components"]
    assert "noop" in SUPPORTED_OPERATION_TYPES
    assert "add_component" in SUPPORTED_OPERATION_TYPES
