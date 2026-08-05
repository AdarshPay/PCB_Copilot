"""Deterministic finding → typed Operation remediations.

Guardrails
----------
* Maps first-pack ``rule_id`` values to reversible IR ``Operation`` lists only.
* Never mutates the input ``Design``; callers apply via the transaction
  compiler on a deep copy / temp branch.
* No CAD file I/O and no production writes. Confidence reflects heuristic
  quality, not datasheet-backed certainty.
* Unsupported rules return an empty list (planner skips them).
"""

from __future__ import annotations

from uuid import uuid4

from pcb_ai_circuit_ir.models import (
    Design,
    ElectricalRole,
    EvidenceRef,
    Finding,
    FunctionalClass,
    Net,
    NetClass,
    Operation,
    RiskTier,
)

# First-pack rules with deterministic remediations (Phase A Day 60 MVP).
SUPPORTED_RULE_IDS: frozenset[str] = frozenset(
    {
        "elec.open_drain_pullup",
        "struct.footprint_presence",
        "elec.undriven_input",
        "elec.power_source",
        "elec.output_conflict",
        "elec.polarity",
        "struct.unique_references",
        "struct.pin_existence",
    }
)

_DEFAULT_PULLUP_VALUE = "4.7k"
_DEFAULT_FOOTPRINT = "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm"
_PASSIVE_FOOTPRINT = "Resistor_SMD:R_0603_1608Metric"


def map_findings_to_operations(design: Design, findings: list[Finding]) -> list[Operation]:
    """Map each finding to zero or more typed operations (deterministic)."""
    ops: list[Operation] = []
    # Track refs allocated within this propose pass so multi-finding batches stay unique.
    reserved_refs = {c.reference for c in design.components}
    for finding in findings:
        mapper = _MAPPERS.get(finding.rule_id)
        if mapper is None:
            continue
        produced = mapper(design, finding, reserved_refs)
        for op in produced:
            if not op.evidence_refs and finding.evidence_refs:
                op.evidence_refs = list(finding.evidence_refs)
            if not op.expected_checks:
                op.expected_checks = [finding.rule_id]
        ops.extend(produced)
    return ops


def _next_ref(prefix: str, reserved: set[str]) -> str:
    for i in range(1, 10_000):
        candidate = f"{prefix}{i}"
        if candidate not in reserved:
            reserved.add(candidate)
            return candidate
    raise RuntimeError(f"Could not allocate reference with prefix {prefix!r}")


def _rule_evidence(rule_id: str, title: str) -> list[EvidenceRef]:
    return [EvidenceRef(id=f"rule:{rule_id}", kind="rule", title=title)]


def _power_net(design: Design) -> Net | None:
    pin_roles: dict[tuple[str, str], ElectricalRole] = {}
    for component in design.components:
        for pin in component.pins:
            pin_roles[(component.reference, pin.number)] = pin.electrical_role
    for net in design.nets:
        if net.net_class == NetClass.POWER:
            return net
        if any(
            pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.POWER_OUT
            for ep in net.endpoints
        ):
            return net
    return None


def _ground_net(design: Design) -> Net | None:
    for net in design.nets:
        if net.net_class == NetClass.GROUND:
            return net
    return None


def _parse_pin_label(label: str) -> tuple[str, str] | None:
    if "." not in label:
        return None
    ref, pin = label.rsplit(".", 1)
    if not ref or not pin:
        return None
    return ref, pin


def _remap_open_drain_pullup(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    if not finding.objects:
        return []
    bus_name = finding.objects[0]
    bus = next((n for n in design.nets if n.name == bus_name), None)
    if bus is None:
        return []
    power = _power_net(design)
    if power is None:
        return []

    ref = _next_ref("R_PU_", reserved)
    component = {
        "reference": ref,
        "value": _DEFAULT_PULLUP_VALUE,
        "functional_class": FunctionalClass.PASSIVE.value,
        "symbol_ref": "Device:R",
        "footprint_ref": _PASSIVE_FOOTPRINT,
        "pins": [
            {"number": "1", "name": "1", "electrical_role": ElectricalRole.PASSIVE.value},
            {"number": "2", "name": "2", "electrical_role": ElectricalRole.PASSIVE.value},
        ],
        "attributes": {"role": "remediation_pullup", "bus_net": bus_name},
        "uuid": str(uuid4()),
    }
    return [
        Operation(
            type="add_component",
            target=ref,
            payload={"component": component},
            preconditions=[f"net_exists:{bus_name}", f"net_exists:{power.name}"],
            postconditions=[f"component_exists:{ref}"],
            expected_checks=["elec.open_drain_pullup"],
            risk_tier=RiskTier.LOW,
            confidence=0.9,
            evidence_refs=_rule_evidence("elec.open_drain_pullup", "Add open-drain pull-up"),
            rollback={"remove_reference": ref},
        ),
        Operation(
            type="add_endpoint",
            target=power.name,
            payload={"component_ref": ref, "pin_number": "1"},
            expected_checks=["elec.open_drain_pullup"],
            risk_tier=RiskTier.LOW,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": "1"},
        ),
        Operation(
            type="add_endpoint",
            target=bus_name,
            payload={"component_ref": ref, "pin_number": "2"},
            expected_checks=["elec.open_drain_pullup"],
            risk_tier=RiskTier.LOW,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": "2"},
        ),
    ]


def _remap_footprint_presence(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    del reserved  # unused
    if not finding.objects:
        return []
    ref = finding.objects[0]
    component = next((c for c in design.components if c.reference == ref), None)
    if component is None:
        return []
    return [
        Operation(
            type="set_footprint_ref",
            target=ref,
            payload={"footprint_ref": _DEFAULT_FOOTPRINT},
            preconditions=[f"component_exists:{ref}"],
            postconditions=[f"footprint_set:{ref}"],
            expected_checks=["struct.footprint_presence"],
            risk_tier=RiskTier.LOW,
            confidence=0.85,
            evidence_refs=_rule_evidence("struct.footprint_presence", "Set placeholder footprint"),
            rollback={"footprint_ref": component.footprint_ref},
        )
    ]


def _remap_undriven_input(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    del reserved
    if not finding.objects:
        return []
    parsed = _parse_pin_label(finding.objects[0])
    if parsed is None:
        return []
    ref, pin_number = parsed
    ground = _ground_net(design)
    if ground is None:
        return []
    # Already attached somewhere? Prefer connecting into the ground rail (valid driver).
    return [
        Operation(
            type="add_endpoint",
            target=ground.name,
            payload={"component_ref": ref, "pin_number": pin_number},
            preconditions=[f"component_exists:{ref}", f"net_exists:{ground.name}"],
            postconditions=[f"pin_driven:{ref}.{pin_number}"],
            expected_checks=["elec.undriven_input"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.8,
            evidence_refs=_rule_evidence("elec.undriven_input", "Tie undriven input to ground"),
            rollback={"component_ref": ref, "pin_number": pin_number},
        )
    ]


def _remap_power_source(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    del reserved
    if not finding.objects:
        return []
    net_name = finding.objects[0]
    net = next((n for n in design.nets if n.name == net_name), None)
    if net is None:
        return []
    return [
        Operation(
            type="set_net_class",
            target=net_name,
            payload={"net_class": NetClass.POWER.value},
            preconditions=[f"net_exists:{net_name}"],
            postconditions=[f"net_class:{net_name}=power"],
            expected_checks=["elec.power_source"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.85,
            evidence_refs=_rule_evidence("elec.power_source", "Mark net as power rail"),
            rollback={"net_class": net.net_class.value},
        )
    ]


def _remap_output_conflict(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    del reserved
    if len(finding.objects) < 3:
        return []
    net_name = finding.objects[0]
    # Disconnect the last listed driver (often the injected fault).
    driver_label = finding.objects[-1]
    parsed = _parse_pin_label(driver_label)
    if parsed is None:
        return []
    ref, pin_number = parsed
    net = next((n for n in design.nets if n.name == net_name), None)
    if net is None:
        return []
    return [
        Operation(
            type="remove_endpoint",
            target=net_name,
            payload={"component_ref": ref, "pin_number": pin_number},
            preconditions=[f"endpoint_on_net:{ref}.{pin_number}@{net_name}"],
            postconditions=[f"endpoint_removed:{ref}.{pin_number}"],
            expected_checks=["elec.output_conflict"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.88,
            evidence_refs=_rule_evidence("elec.output_conflict", "Disconnect conflicting driver"),
            rollback={
                "component_ref": ref,
                "pin_number": pin_number,
                "pin_name": next(
                    (
                        ep.pin_name
                        for ep in net.endpoints
                        if ep.component_ref == ref and ep.pin_number == pin_number
                    ),
                    None,
                ),
            },
        )
    ]


def _remap_polarity(design: Design, finding: Finding, reserved: set[str]) -> list[Operation]:
    del reserved
    if len(finding.objects) < 3:
        return []
    ref = finding.objects[0]
    pos = _parse_pin_label(finding.objects[1])
    neg = _parse_pin_label(finding.objects[2])
    if pos is None or neg is None:
        return []
    _, pos_pin = pos
    _, neg_pin = neg

    power = _power_net(design)
    ground = _ground_net(design)
    if power is None or ground is None:
        return []

    # Finding means + on ground, - on power. Swap: + → power, - → ground.
    return [
        Operation(
            type="remove_endpoint",
            target=ground.name,
            payload={"component_ref": ref, "pin_number": pos_pin},
            expected_checks=["elec.polarity"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": pos_pin},
        ),
        Operation(
            type="remove_endpoint",
            target=power.name,
            payload={"component_ref": ref, "pin_number": neg_pin},
            expected_checks=["elec.polarity"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": neg_pin},
        ),
        Operation(
            type="add_endpoint",
            target=power.name,
            payload={"component_ref": ref, "pin_number": pos_pin},
            expected_checks=["elec.polarity"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": pos_pin},
        ),
        Operation(
            type="add_endpoint",
            target=ground.name,
            payload={"component_ref": ref, "pin_number": neg_pin},
            expected_checks=["elec.polarity"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.9,
            rollback={"component_ref": ref, "pin_number": neg_pin},
        ),
    ]


def _remap_unique_references(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    if not finding.objects:
        return []
    dup_ref = finding.objects[0]
    matches = [c for c in design.components if c.reference == dup_ref]
    if len(matches) < 2:
        return []
    # Keep the first occurrence; rename later duplicates.
    victim = matches[-1]
    # Prefer a stable rename prefix from the original ref.
    prefix = "".join(ch for ch in dup_ref if ch.isalpha()) or "U"
    if not prefix.endswith("_"):
        prefix = f"{prefix}_FIX_"
    new_ref = _next_ref(prefix, reserved)
    # Ensure the original dup_ref stays reserved as the kept designator.
    reserved.add(dup_ref)
    return [
        Operation(
            type="rename_component",
            target=dup_ref,
            payload={"new_reference": new_ref, "uuid": victim.uuid},
            preconditions=[f"duplicate_reference:{dup_ref}"],
            postconditions=[f"unique_reference:{new_ref}"],
            expected_checks=["struct.unique_references"],
            risk_tier=RiskTier.LOW,
            confidence=0.92,
            evidence_refs=_rule_evidence("struct.unique_references", "Rename duplicate reference"),
            rollback={"old_reference": dup_ref, "uuid": victim.uuid},
        )
    ]


def _remap_pin_existence(
    design: Design, finding: Finding, reserved: set[str]
) -> list[Operation]:
    del reserved
    # objects: [net.name, component_ref, pin_number]
    if len(finding.objects) < 3:
        return []
    net_name, ref, pin_number = finding.objects[0], finding.objects[1], finding.objects[2]
    net = next((n for n in design.nets if n.name == net_name), None)
    if net is None:
        return []
    return [
        Operation(
            type="remove_endpoint",
            target=net_name,
            payload={"component_ref": ref, "pin_number": pin_number},
            expected_checks=["struct.pin_existence"],
            risk_tier=RiskTier.MEDIUM,
            confidence=0.8,
            evidence_refs=_rule_evidence("struct.pin_existence", "Remove dangling endpoint"),
            rollback={"component_ref": ref, "pin_number": pin_number},
        )
    ]


_MAPPERS = {
    "elec.open_drain_pullup": _remap_open_drain_pullup,
    "struct.footprint_presence": _remap_footprint_presence,
    "elec.undriven_input": _remap_undriven_input,
    "elec.power_source": _remap_power_source,
    "elec.output_conflict": _remap_output_conflict,
    "elec.polarity": _remap_polarity,
    "struct.unique_references": _remap_unique_references,
    "struct.pin_existence": _remap_pin_existence,
}
