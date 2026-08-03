"""Circuit IR v0 Pydantic models.

The circuit IR is the source of truth for AI reasoning. Nets are hyperedges
connecting multiple component pins. Relational storage is PostgreSQL-first;
graph projections are derived for algorithms.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SourceTool(StrEnum):
    KICAD = "kicad"
    ALTIUM = "altium"
    SYNTHETIC = "synthetic"


class FunctionalClass(StrEnum):
    MCU = "mcu"
    SENSOR = "sensor"
    REGULATOR_LDO = "regulator_ldo"
    REGULATOR_BUCK = "regulator_buck"
    TRANSCEIVER = "transceiver"
    CONNECTOR = "connector"
    PASSIVE = "passive"
    PROTECTION = "protection"
    INTERFACE_BRIDGE = "interface_bridge"
    PROGRAMMING = "programming"
    TEST = "test"
    OTHER = "other"


class ElectricalRole(StrEnum):
    POWER_IN = "power_in"
    POWER_OUT = "power_out"
    GROUND = "ground"
    DIGITAL_IN = "digital_in"
    DIGITAL_OUT = "digital_out"
    DIGITAL_BIDIR = "digital_bidir"
    OPEN_DRAIN = "open_drain"
    ANALOG_IN = "analog_in"
    ANALOG_OUT = "analog_out"
    CLOCK = "clock"
    RESET = "reset"
    BOOT = "boot"
    ENABLE = "enable"
    NO_CONNECT = "no_connect"
    PASSIVE = "passive"
    UNSPECIFIED = "unspecified"


class NetClass(StrEnum):
    POWER = "power"
    GROUND = "ground"
    SIGNAL = "signal"
    BUS = "bus"
    DIFFERENTIAL = "differential"
    UNSPECIFIED = "unspecified"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceLocation(Model):
    """Pointer back into the source CAD artifact."""

    sheet: str | None = None
    uuid: str | None = None
    path: str | None = None
    x: float | None = None
    y: float | None = None


class Constraint(Model):
    name: str
    operator: str = Field(description="e.g. eq, ne, lt, lte, gt, gte, in, between")
    value: Any
    unit: str | None = None
    notes: str | None = None


class EvidenceRef(Model):
    """Citation into curated facts, datasheets, rules, or prior findings."""

    id: str
    kind: str = Field(description="rule | datasheet | component_profile | fixture | erc | note")
    title: str | None = None
    uri: str | None = None
    page: int | None = None
    excerpt: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Requirement(Model):
    id: str
    text: str
    priority: str = "should"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class Block(Model):
    id: str
    name: str
    description: str | None = None
    component_refs: list[str] = Field(default_factory=list)


class Pin(Model):
    number: str
    name: str
    electrical_role: ElectricalRole = ElectricalRole.UNSPECIFIED
    interface_role: str | None = None
    voltage_domain: str | None = None
    constraints: list[Constraint] = Field(default_factory=list)


class Component(Model):
    reference: str
    manufacturer_part_number: str | None = None
    value: str | None = None
    functional_class: FunctionalClass = FunctionalClass.OTHER
    symbol_ref: str | None = None
    footprint_ref: str | None = None
    pins: list[Pin] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_location: SourceLocation | None = None
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Endpoint(Model):
    """A pin on a component attached to a net (hyperedge member)."""

    component_ref: str
    pin_number: str
    pin_name: str | None = None


class Net(Model):
    name: str
    endpoints: list[Endpoint] = Field(default_factory=list)
    net_class: NetClass = Field(default=NetClass.UNSPECIFIED, alias="class")
    voltage_domain: str | None = None
    protocol: str | None = None
    constraints: list[Constraint] = Field(default_factory=list)
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Assertion(Model):
    id: str
    kind: str
    expression: str
    severity: Severity = Severity.ERROR
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class Design(Model):
    """Top-level typed circuit IR document."""

    id: str
    source_tool: SourceTool = SourceTool.KICAD
    source_version: str | None = None
    revision: str = "0"
    name: str | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    nets: list[Net] = Field(default_factory=list)
    assertions: list[Assertion] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class Operation(Model):
    """Typed, reversible edit proposal. Never applied directly to production CAD."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    target: str
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    expected_checks: list[str] = Field(default_factory=list)
    risk_tier: RiskTier = RiskTier.MEDIUM
    rollback: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Finding(Model):
    """Normalized verifier / ERC / semantic finding."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    severity: Severity
    objects: list[str] = Field(default_factory=list)
    explanation: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    remediation_operations: list[Operation] = Field(default_factory=list)
    source: str = "deterministic"


class ReviewReport(Model):
    """Machine-readable review artifact for a design revision."""

    id: UUID = Field(default_factory=uuid4)
    design_id: str
    design_revision: str
    findings: list[Finding] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
