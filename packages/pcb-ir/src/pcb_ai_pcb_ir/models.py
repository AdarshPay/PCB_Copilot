"""Board / PCB IR models for Phase B layout.

Circuit IR remains the electrical source of truth. Board IR carries placement,
copper, and geometry for place/route under DRC gates.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pcb_ai_circuit_ir.models import EvidenceRef, Finding, Operation


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Layer(StrEnum):
    F_CU = "F.Cu"
    B_CU = "B.Cu"
    F_SILK = "F.SilkS"
    B_SILK = "B.SilkS"
    F_MASK = "F.Mask"
    B_MASK = "B.Mask"
    EDGE_CUTS = "Edge.Cuts"
    F_CRTYD = "F.CrtYd"
    B_CRTYD = "B.CrtYd"


class Point(Model):
    x: float
    y: float


class Placement(Model):
    x: float = 0.0
    y: float = 0.0
    rotation_deg: float = 0.0
    layer: Layer = Layer.F_CU
    placed: bool = False


class Pad(Model):
    number: str
    name: str | None = None
    net_name: str | None = None
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    shape: str = "rect"
    layers: list[Layer] = Field(default_factory=lambda: [Layer.F_CU])


class FootprintInstance(Model):
    reference: str
    footprint_ref: str
    value: str | None = None
    placement: Placement = Field(default_factory=Placement)
    pads: list[Pad] = Field(default_factory=list)
    courtyard_width: float = 5.0
    courtyard_height: float = 5.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Track(Model):
    net_name: str
    layer: Layer = Layer.F_CU
    start: Point
    end: Point
    width: float = 0.25
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Via(Model):
    net_name: str
    at: Point
    size: float = 0.6
    drill: float = 0.3
    layers: list[Layer] = Field(default_factory=lambda: [Layer.F_CU, Layer.B_CU])
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Zone(Model):
    net_name: str | None = None
    layer: Layer = Layer.B_CU
    points: list[Point] = Field(default_factory=list)
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Outline(Model):
    """Rectangular board outline on Edge.Cuts (MVP)."""

    width: float = 50.0
    height: float = 40.0
    origin: Point = Field(default_factory=lambda: Point(x=0.0, y=0.0))


class BoardConstraint(Model):
    name: str
    value: Any
    unit: str | None = None
    notes: str | None = None


class BoardNet(Model):
    name: str
    class_name: str = "Default"
    uuid: str = Field(default_factory=lambda: str(uuid4()))


class Board(Model):
    """Top-level board document for place/route."""

    id: str
    design_id: str | None = None
    source_tool: str = "kicad"
    source_version: str | None = None
    revision: str = "0"
    name: str | None = None
    outline: Outline = Field(default_factory=Outline)
    layers: list[Layer] = Field(default_factory=lambda: [Layer.F_CU, Layer.B_CU])
    footprints: list[FootprintInstance] = Field(default_factory=list)
    nets: list[BoardNet] = Field(default_factory=list)
    tracks: list[Track] = Field(default_factory=list)
    vias: list[Via] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    constraints: list[BoardConstraint] = Field(default_factory=list)
    unrouted_nets: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


# Documented layout operation type strings (payload shapes vary by type).
LAYOUT_OPERATION_TYPES: frozenset[str] = frozenset(
    {
        "place_footprint",
        "move_footprint",
        "rotate_footprint",
        "add_track",
        "add_via",
        "set_board_outline",
        "set_net_class_rule",
        "ripup_net",
    }
)

__all__ = [
    "Board",
    "BoardConstraint",
    "BoardNet",
    "FootprintInstance",
    "Layer",
    "LAYOUT_OPERATION_TYPES",
    "Outline",
    "Pad",
    "Placement",
    "Point",
    "Track",
    "Via",
    "Zone",
]
