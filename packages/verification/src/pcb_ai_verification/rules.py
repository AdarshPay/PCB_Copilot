"""First high-precision deterministic rule pack (subset for foundations)."""

from __future__ import annotations

from collections.abc import Callable

from pcb_ai_circuit_ir.models import (
    Component,
    Design,
    ElectricalRole,
    EvidenceRef,
    Finding,
    FunctionalClass,
    Net,
    NetClass,
    Pin,
    Severity,
)

RuleFn = Callable[[Design], list[Finding]]

# Explicit input roles that must be driven for high-precision undriven checks.
REQUIRED_INPUT_ROLES: frozenset[ElectricalRole] = frozenset(
    {
        ElectricalRole.DIGITAL_IN,
        ElectricalRole.ANALOG_IN,
        ElectricalRole.RESET,
        ElectricalRole.ENABLE,
        ElectricalRole.BOOT,
        ElectricalRole.CLOCK,
    }
)

# Roles that can drive a net for undriven-input purposes.
NET_DRIVER_ROLES: frozenset[ElectricalRole] = frozenset(
    {
        ElectricalRole.DIGITAL_OUT,
        ElectricalRole.ANALOG_OUT,
        ElectricalRole.POWER_OUT,
        ElectricalRole.OPEN_DRAIN,
        ElectricalRole.DIGITAL_BIDIR,
        ElectricalRole.GROUND,
    }
)

OUTPUT_DRIVER_ROLES: frozenset[ElectricalRole] = frozenset(
    {
        ElectricalRole.DIGITAL_OUT,
        ElectricalRole.ANALOG_OUT,
        ElectricalRole.POWER_OUT,
    }
)

# Protocols that require a passive pull-up to a power rail (explicit IR annotation).
PULLUP_REQUIRED_PROTOCOLS: frozenset[str] = frozenset({"i2c"})


def _pin_roles(design: Design) -> dict[tuple[str, str], ElectricalRole]:
    roles: dict[tuple[str, str], ElectricalRole] = {}
    for component in design.components:
        for pin in component.pins:
            roles[(component.reference, pin.number)] = pin.electrical_role
    return roles


def _pin_index(design: Design) -> dict[tuple[str, str], Pin]:
    index: dict[tuple[str, str], Pin] = {}
    for component in design.components:
        for pin in component.pins:
            index[(component.reference, pin.number)] = pin
    return index


def _components_by_ref(design: Design) -> dict[str, Component]:
    return {component.reference: component for component in design.components}


def _net_has_driver(net: Net, pin_roles: dict[tuple[str, str], ElectricalRole]) -> bool:
    """True if the net is externally supplied or has an active/passive driver pin."""
    if net.net_class in {NetClass.POWER, NetClass.GROUND}:
        return True
    return any(
        pin_roles.get((ep.component_ref, ep.pin_number)) in NET_DRIVER_ROLES
        for ep in net.endpoints
    )


def _is_power_rail(net: Net, pin_roles: dict[tuple[str, str], ElectricalRole]) -> bool:
    """True when the net is classed as power or has a modeled power_out driver."""
    if net.net_class == NetClass.POWER:
        return True
    return any(
        pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.POWER_OUT
        for ep in net.endpoints
    )


def _is_ground_rail(net: Net, pin_roles: dict[tuple[str, str], ElectricalRole]) -> bool:
    if net.net_class == NetClass.GROUND:
        return True
    return any(
        pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.GROUND
        for ep in net.endpoints
    )


def _nets_for_pin(design: Design, component_ref: str, pin_number: str) -> list[Net]:
    return [
        net
        for net in design.nets
        if any(
            ep.component_ref == component_ref and ep.pin_number == pin_number
            for ep in net.endpoints
        )
    ]


def _net_requires_pullup(net: Net, pin_roles: dict[tuple[str, str], ElectricalRole]) -> bool:
    """Open-drain endpoints or an explicit I2C protocol annotation require a pull-up."""
    if any(
        pin_roles.get((ep.component_ref, ep.pin_number)) == ElectricalRole.OPEN_DRAIN
        for ep in net.endpoints
    ):
        return True
    protocol = (net.protocol or "").strip().lower()
    return protocol in PULLUP_REQUIRED_PROTOCOLS


def _net_has_passive_pullup_to_power(
    net: Net,
    design: Design,
    pin_roles: dict[tuple[str, str], ElectricalRole],
    comps: dict[str, Component],
) -> bool:
    """True if a passive bridges this net to a power rail (classic I2C pull-up)."""
    for ep in net.endpoints:
        component = comps.get(ep.component_ref)
        if component is None or component.functional_class != FunctionalClass.PASSIVE:
            continue
        for other_pin in component.pins:
            if other_pin.number == ep.pin_number:
                continue
            for other_net in _nets_for_pin(design, component.reference, other_pin.number):
                if other_net is net:
                    continue
                if _is_power_rail(other_net, pin_roles):
                    return True
    return False


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
    pin_roles = _pin_roles(design)
    findings: list[Finding] = []
    for net in design.nets:
        drivers = [
            ep
            for ep in net.endpoints
            if pin_roles.get((ep.component_ref, ep.pin_number)) in OUTPUT_DRIVER_ROLES
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


def check_undriven_inputs(design: Design) -> list[Finding]:
    """Electrical: required input pins must attach to a driven net."""
    pin_roles = _pin_roles(design)
    pin_to_nets: dict[tuple[str, str], list[Net]] = {}
    for net in design.nets:
        for ep in net.endpoints:
            pin_to_nets.setdefault((ep.component_ref, ep.pin_number), []).append(net)

    findings: list[Finding] = []
    for component in design.components:
        for pin in component.pins:
            if pin.electrical_role not in REQUIRED_INPUT_ROLES:
                continue
            key = (component.reference, pin.number)
            nets = pin_to_nets.get(key, [])
            if not nets or not any(_net_has_driver(net, pin_roles) for net in nets):
                objects = [f"{component.reference}.{pin.number}"]
                if nets:
                    objects.extend(net.name for net in nets)
                findings.append(
                    Finding(
                        rule_id="elec.undriven_input",
                        severity=Severity.ERROR,
                        objects=objects,
                        explanation=(
                            f"Required input {component.reference}.{pin.number} "
                            f"({pin.electrical_role.value}) has no driven net."
                        ),
                        evidence_refs=[
                            EvidenceRef(
                                id="rule:elec.undriven_input",
                                kind="rule",
                                title="Undriven required inputs",
                            )
                        ],
                    )
                )
    return findings


def check_power_source(design: Design) -> list[Finding]:
    """Electrical: power-input pins must attach to a net with a power source."""
    pin_roles = _pin_roles(design)
    power_out_nets: set[str] = set()
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
        # Allow nets explicitly classed as power even without a modeled source (e.g. board VIN).
        if (
            has_power_in
            and net.name not in power_out_nets
            and net.net_class != NetClass.POWER
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


def check_open_drain_pullup(design: Design) -> list[Finding]:
    """Electrical: open-drain / I2C buses need a passive pull-up to a power rail.

    Assumptions (high precision):
    - Only nets with an open_drain endpoint or protocol='i2c' are checked.
    - A valid pull-up is a PASSIVE component bridging the bus net to a power rail
      (net_class=power or a power_out driver). Active/internal pull-ups are ignored.
    """
    pin_roles = _pin_roles(design)
    comps = _components_by_ref(design)
    findings: list[Finding] = []
    for net in design.nets:
        if not _net_requires_pullup(net, pin_roles):
            continue
        if _net_has_passive_pullup_to_power(net, design, pin_roles, comps):
            continue
        findings.append(
            Finding(
                rule_id="elec.open_drain_pullup",
                severity=Severity.ERROR,
                objects=[net.name],
                explanation=(
                    f"Open-drain/I2C net {net.name!r} has no passive pull-up to a power rail."
                ),
                evidence_refs=[
                    EvidenceRef(
                        id="rule:elec.open_drain_pullup",
                        kind="rule",
                        title="Open-drain bus without required pull-up",
                    )
                ],
            )
        )
    return findings


def check_voltage_domain(design: Design) -> list[Finding]:
    """Electrical: declared voltage domains on one net must agree.

    Assumptions (high precision):
    - Only explicit non-null pin.voltage_domain and net.voltage_domain values participate.
    - Comparison is exact string equality (e.g. '3V3' vs '5V'); undeclared pins are ignored.
    """
    pins = _pin_index(design)
    findings: list[Finding] = []
    for net in design.nets:
        domains: set[str] = set()
        if net.voltage_domain:
            domains.add(net.voltage_domain)
        for ep in net.endpoints:
            pin = pins.get((ep.component_ref, ep.pin_number))
            if pin is not None and pin.voltage_domain:
                domains.add(pin.voltage_domain)
        if len(domains) > 1:
            findings.append(
                Finding(
                    rule_id="elec.voltage_domain",
                    severity=Severity.ERROR,
                    objects=[net.name, *sorted(domains)],
                    explanation=(
                        f"Net {net.name!r} mixes incompatible voltage domains: "
                        f"{', '.join(sorted(domains))}."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            id="rule:elec.voltage_domain",
                            kind="rule",
                            title="Voltage-domain incompatibility",
                        )
                    ],
                )
            )
    return findings


def check_polarity(design: Design) -> list[Finding]:
    """Electrical: polarized parts must not be reversed across power/ground.

    Assumptions (high precision):
    - Only components with attributes.polarized truthy are checked (explicit opt-in).
    - positive_pin/anode_pin and negative_pin/cathode_pin identify terminals.
    - Reversed means the positive terminal is on a ground rail while the negative
      terminal is on a power rail. Other orientations are not flagged.
    """
    pin_roles = _pin_roles(design)
    findings: list[Finding] = []
    for component in design.components:
        attrs = component.attributes or {}
        if not attrs.get("polarized"):
            continue
        positive = attrs.get("positive_pin") or attrs.get("anode_pin")
        negative = attrs.get("negative_pin") or attrs.get("cathode_pin")
        if not positive or not negative:
            continue
        positive = str(positive)
        negative = str(negative)
        pos_nets = _nets_for_pin(design, component.reference, positive)
        neg_nets = _nets_for_pin(design, component.reference, negative)
        if not pos_nets or not neg_nets:
            continue
        pos_on_gnd = any(_is_ground_rail(net, pin_roles) for net in pos_nets)
        neg_on_pwr = any(_is_power_rail(net, pin_roles) for net in neg_nets)
        if pos_on_gnd and neg_on_pwr:
            findings.append(
                Finding(
                    rule_id="elec.polarity",
                    severity=Severity.ERROR,
                    objects=[
                        component.reference,
                        f"{component.reference}.{positive}",
                        f"{component.reference}.{negative}",
                    ],
                    explanation=(
                        f"Polarized component {component.reference} appears reversed "
                        f"(positive on ground, negative on power)."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            id="rule:elec.polarity",
                            kind="rule",
                            title="Polarity-sensitive device orientation",
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
    ("elec.undriven_input", check_undriven_inputs),
    ("elec.power_source", check_power_source),
    ("elec.open_drain_pullup", check_open_drain_pullup),
    ("elec.voltage_domain", check_voltage_domain),
    ("elec.polarity", check_polarity),
]
