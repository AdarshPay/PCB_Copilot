"""Curated offline evidence catalog for RULE_PACK_V0 and placeholder parts."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import EvidenceRef

# Canonical rule evidence: id == f"rule:{rule_id}"
RULE_EVIDENCE: dict[str, EvidenceRef] = {
    "struct.schema_validity": EvidenceRef(
        id="rule:struct.schema_validity",
        kind="rule",
        title="Schema validity",
        uri="pcb-ai://rules/struct.schema_validity",
        excerpt="Design documents must include a non-empty id and satisfy the circuit IR schema.",
        confidence=1.0,
    ),
    "struct.unique_references": EvidenceRef(
        id="rule:struct.unique_references",
        kind="rule",
        title="Unique references",
        uri="pcb-ai://rules/struct.unique_references",
        excerpt="Each component reference designator must be unique within a design.",
        confidence=1.0,
    ),
    "struct.pin_existence": EvidenceRef(
        id="rule:struct.pin_existence",
        kind="rule",
        title="Referenced pin existence",
        uri="pcb-ai://rules/struct.pin_existence",
        excerpt="Net endpoints must reference pins that exist on the named component.",
        confidence=1.0,
    ),
    "struct.footprint_presence": EvidenceRef(
        id="rule:struct.footprint_presence",
        kind="rule",
        title="Footprint presence",
        uri="pcb-ai://rules/struct.footprint_presence",
        excerpt=(
            "Placement-bound functional classes (MCU, sensor, regulator, etc.) "
            "must declare a footprint_ref."
        ),
        confidence=1.0,
    ),
    "elec.output_conflict": EvidenceRef(
        id="rule:elec.output_conflict",
        kind="rule",
        title="Output-to-output conflicts",
        uri="pcb-ai://rules/elec.output_conflict",
        excerpt="A net must not have more than one actively driven output endpoint.",
        confidence=1.0,
    ),
    "elec.undriven_input": EvidenceRef(
        id="rule:elec.undriven_input",
        kind="rule",
        title="Undriven required inputs",
        uri="pcb-ai://rules/elec.undriven_input",
        excerpt="Required input pins must attach to a net that has a modeled driver.",
        confidence=1.0,
    ),
    "elec.power_source": EvidenceRef(
        id="rule:elec.power_source",
        kind="rule",
        title="Power-input nets without a valid source",
        uri="pcb-ai://rules/elec.power_source",
        excerpt=(
            "Nets with power_in endpoints should connect to a modeled power_out source "
            "or be explicitly classed as power (e.g. board VIN)."
        ),
        confidence=1.0,
    ),
    "elec.open_drain_pullup": EvidenceRef(
        id="rule:elec.open_drain_pullup",
        kind="rule",
        title="Open-drain bus without required pull-up",
        uri="pcb-ai://rules/elec.open_drain_pullup",
        excerpt=(
            "Open-drain and I2C buses require a passive pull-up to a power rail. "
            "See also component_profile / datasheet notes for bus devices."
        ),
        confidence=1.0,
    ),
    "elec.voltage_domain": EvidenceRef(
        id="rule:elec.voltage_domain",
        kind="rule",
        title="Voltage-domain incompatibility",
        uri="pcb-ai://rules/elec.voltage_domain",
        excerpt=(
            "Declared pin and net voltage_domain values on one net must agree "
            "(exact string equality)."
        ),
        confidence=1.0,
    ),
    "elec.polarity": EvidenceRef(
        id="rule:elec.polarity",
        kind="rule",
        title="Polarity-sensitive device orientation",
        uri="pcb-ai://rules/elec.polarity",
        excerpt=(
            "Polarized components (attributes.polarized) must not place the positive "
            "terminal on ground while the negative terminal is on a power rail."
        ),
        confidence=1.0,
    ),
}

# Related notes / datasheet / profile placeholders keyed by rule_id
RELATED_BY_RULE: dict[str, list[EvidenceRef]] = {
    "elec.open_drain_pullup": [
        EvidenceRef(
            id="note:i2c_pullup_practice",
            kind="note",
            title="I2C pull-up practice",
            uri="pcb-ai://notes/i2c_pullup_practice",
            excerpt="Typical I2C SDA/SCL buses use external resistors to VDD (often 2.2k–10k).",
            confidence=0.9,
        ),
        EvidenceRef(
            id="datasheet:TMP117",
            kind="datasheet",
            title="TMP117 datasheet (I2C open-drain)",
            uri="pcb-ai://datasheets/TMP117",
            page=1,
            excerpt="SDA and SCL are open-drain; external pull-ups to V+ are required.",
            confidence=0.85,
        ),
    ],
    "elec.power_source": [
        EvidenceRef(
            id="datasheet:AP2112K-3.3",
            kind="datasheet",
            title="AP2112K-3.3 LDO datasheet placeholder",
            uri="pcb-ai://datasheets/AP2112K-3.3",
            page=1,
            excerpt="VOUT is the regulated output rail; local input/output capacitors recommended.",
            confidence=0.8,
        ),
        EvidenceRef(
            id="component_profile:AP2112K-3.3",
            kind="component_profile",
            title="AP2112K-3.3 curated profile placeholder",
            uri="pcb-ai://profiles/AP2112K-3.3",
            excerpt="Curated LDO profile: power_out on VOUT, power_in on VIN, ground on GND.",
            confidence=0.85,
        ),
    ],
    "elec.voltage_domain": [
        EvidenceRef(
            id="note:voltage_domain_labels",
            kind="note",
            title="Voltage domain labeling",
            uri="pcb-ai://notes/voltage_domain_labels",
            excerpt="Use consistent labels (e.g. 3V3, 5V, GND) across pins and nets.",
            confidence=0.9,
        ),
    ],
    "elec.polarity": [
        EvidenceRef(
            id="note:polarized_passives",
            kind="note",
            title="Polarized passive orientation",
            uri="pcb-ai://notes/polarized_passives",
            excerpt="Electrolytic/tantalum caps and diodes must match power/ground polarity.",
            confidence=0.9,
        ),
    ],
    "struct.footprint_presence": [
        EvidenceRef(
            id="component_profile:RP2040",
            kind="component_profile",
            title="RP2040 curated profile placeholder",
            uri="pcb-ai://profiles/RP2040",
            excerpt="MCU profile expects a QFN-56 footprint_ref for placement-bound designs.",
            confidence=0.85,
        ),
    ],
}

# Standalone datasheet / profile placeholders (also searchable)
STANDALONE_PLACEHOLDERS: list[EvidenceRef] = [
    EvidenceRef(
        id="datasheet:RP2040",
        kind="datasheet",
        title="RP2040 datasheet placeholder",
        uri="pcb-ai://datasheets/RP2040",
        page=1,
        excerpt="Offline placeholder citation for Raspberry Pi RP2040 MCU.",
        confidence=0.75,
    ),
    EvidenceRef(
        id="datasheet:CP2102",
        kind="datasheet",
        title="CP2102 datasheet placeholder",
        uri="pcb-ai://datasheets/CP2102",
        page=1,
        excerpt="Offline placeholder citation for Silicon Labs CP2102 USB-UART bridge.",
        confidence=0.75,
    ),
    EvidenceRef(
        id="component_profile:TMP117",
        kind="component_profile",
        title="TMP117 curated profile placeholder",
        uri="pcb-ai://profiles/TMP117",
        excerpt="Temperature sensor profile: open-drain I2C pins require external pull-ups.",
        confidence=0.85,
    ),
    EvidenceRef(
        id="component_profile:CP2102",
        kind="component_profile",
        title="CP2102 curated profile placeholder",
        uri="pcb-ai://profiles/CP2102",
        excerpt="USB-UART bridge profile placeholder for UART bridge fixtures.",
        confidence=0.8,
    ),
]


def all_seed_refs() -> list[EvidenceRef]:
    """Flatten rule, related, and standalone catalog entries (deduped by id)."""
    by_id: dict[str, EvidenceRef] = {}
    for ref in RULE_EVIDENCE.values():
        by_id[ref.id] = ref
    for refs in RELATED_BY_RULE.values():
        for ref in refs:
            by_id[ref.id] = ref
    for ref in STANDALONE_PLACEHOLDERS:
        by_id[ref.id] = ref
    return list(by_id.values())


def normalize_rule_id(rule_id: str) -> str:
    """Accept ``struct.x`` or ``rule:struct.x`` and return the bare rule id."""
    text = rule_id.strip()
    if text.startswith("rule:"):
        return text[len("rule:") :]
    return text


def rule_evidence_id(rule_id: str) -> str:
    return f"rule:{normalize_rule_id(rule_id)}"
