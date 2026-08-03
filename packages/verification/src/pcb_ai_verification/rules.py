"""First high-precision deterministic rule pack (subset for foundations)."""

from __future__ import annotations

from collections.abc import Callable

from pcb_ai_circuit_ir.models import Design, ElectricalRole, EvidenceRef, Finding, Severity

RuleFn = Callable[[Design], list[Finding]]


def check_parse_schema(design: Design) -> list[Finding]:
    """Structural: schema-level presence of required collections."""
    findings: list[Finding] = []
    if not design.id:
        findings.append(
            Finding(
                rule_id="struct.schema_validity",
                severity=Severity.ERROR,
                objects=[],
                explanation="Design.id is required.",
                evidence_refs=[
                    EvidenceRef(id="rule:struct.schema_validity", kind="rule", title="Schema validity")
                ],
            )
        )
    return findings


def check_unique_references(design: Design) -> list[Finding]:
    """Structural: component references must be unique."""
    seen: dict[str, str] = {}
    findings: list[Finding] = []
    for component in design.components:
        if component.reference in seen:
            findings.append(
                Finding(
                    rule_id="struct.unique_references",
                    severity=Severity.ERROR,
                    objects=[component.reference, seen[component.reference]],
                    explanation=f"Duplicate component reference {component.reference!r}.",
                    evidence_refs=[
                        EvidenceRef(
                            id="rule:struct.unique_references",
                            kind="rule",
                            title="Unique references",
                        )
                    ],
                )
            )
        else:
            seen[component.reference] = component.uuid
    return findings


def check_pin_existence(design: Design) -> list[Finding]:
    """Structural: net endpoints must reference existing component pins."""
    pin_index: dict[tuple[str, str], str] = {}
    for component in design.components:
        for pin in component.pins:
            pin_index[(component.reference, pin.number)] = pin.name

    findings: list[Finding] = []
    for net in design.nets:
        for endpoint in net.endpoints:
            key = (endpoint.component_ref, endpoint.pin_number)
            if key not in pin_index:
                findings.append(
                    Finding(
                        rule_id="struct.pin_existence",
                        severity=Severity.ERROR,
                        objects=[net.name, endpoint.component_ref, endpoint.pin_number],
                        explanation=(
                            f"Net {net.name!r} references missing pin "
                            f"{endpoint.component_ref}.{endpoint.pin_number}."
                        ),
                        evidence_refs=[
                            EvidenceRef(
                                id="rule:struct.pin_existence",
                                kind="rule",
                                title="Referenced pin existence",
                            )
                        ],
                    )
                )
    return findings


def check_output_conflicts(design: Design) -> list[Finding]:
    """Electrical: two driven outputs on the same net."""
    pin_roles: dict[tuple[str, str], ElectricalRole] = {}
    for component in design.components:
        for pin in component.pins:
            pin_roles[(component.reference, pin.number)] = pin.electrical_role

    driven = {ElectricalRole.DIGITAL_OUT, ElectricalRole.ANALOG_OUT, ElectricalRole.POWER_OUT}
    findings: list[Finding] = []
    for net in design.nets:
        drivers = [
            ep
            for ep in net.endpoints
            if pin_roles.get((ep.component_ref, ep.pin_number)) in driven
        ]
        if len(drivers) > 1:
            objects = [net.name] + [f"{d.component_ref}.{d.pin_number}" for d in drivers]
            findings.append(
                Finding(
                    rule_id="elec.output_conflict",
                    severity=Severity.ERROR,
                    objects=objects,
                    explanation=f"Net {net.name!r} has multiple output drivers.",
                    evidence_refs=[
                        EvidenceRef(
                            id="rule:elec.output_conflict",
                            kind="rule",
                            title="Output-to-output conflicts",
                        )
                    ],
                )
            )
    return findings


def check_power_source(design: Design) -> list[Finding]:
    """Electrical: power-input pins must attach to a net with a power source."""
    power_out_nets: set[str] = set()
    pin_roles: dict[tuple[str, str], ElectricalRole] = {}
    for component in design.components:
        for pin in component.pins:
            pin_roles[(component.reference, pin.number)] = pin.electrical_role

    for net in design.nets:
        for ep in net.endpoints:
            if pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.POWER_OUT:
                power_out_nets.add(net.name)

    findings: list[Finding] = []
    for net in design.nets:
        has_power_in = any(
            pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.POWER_IN
            for ep in net.endpoints
        )
        if has_power_in and net.name not in power_out_nets and net.net_class.value != "power":
            # Allow nets explicitly classed as power even without modeled source yet.
            if not any(
                pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.POWER_OUT
                for ep in net.endpoints
            ):
                findings.append(
                    Finding(
                        rule_id="elec.power_source",
                        severity=Severity.WARNING,
                        objects=[net.name],
                        explanation=(
                            f"Power-input net {net.name!r} has no modeled power source."
                        ),
                        evidence_refs=[
                            EvidenceRef(
                                id="rule:elec.power_source",
                                kind="rule",
                                title="Power-input nets without a valid source",
                            )
                        ],
                    )
                )
    return findings


RULE_PACK_V0: list[tuple[str, RuleFn]] = [
    ("struct.schema_validity", check_parse_schema),
    ("struct.unique_references", check_unique_references),
    ("struct.pin_existence", check_pin_existence),
    ("elec.output_conflict", check_output_conflicts),
    ("elec.power_source", check_power_source),
]
