"""PCB / board intermediate representation (Phase B)."""

from pcb_ai_pcb_ir.models import (
    LAYOUT_OPERATION_TYPES,
    Board,
    BoardConstraint,
    BoardNet,
    FootprintInstance,
    Layer,
    Outline,
    Pad,
    Placement,
    Point,
    Track,
    Via,
    Zone,
)

__version__ = "0.1.0"

__all__ = [
    "LAYOUT_OPERATION_TYPES",
    "Board",
    "BoardConstraint",
    "BoardNet",
    "FootprintInstance",
    "Layer",
    "Outline",
    "Pad",
    "Placement",
    "Point",
    "Track",
    "Via",
    "Zone",
    "__version__",
]
