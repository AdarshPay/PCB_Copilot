"""Layout backend protocol and planner (Phase B)."""

from __future__ import annotations

from typing import Protocol

from pcb_ai_circuit_ir.models import Design, Finding
from pcb_ai_pcb_ir.models import Board


class LayoutBackend(Protocol):
    """Place and route a Board derived from a verified Design."""

    def layout(self, design: Design, board: Board) -> Board:
        """Return a placed/routed board copy; may append findings/operations."""
        ...


class LayoutNotImplemented(RuntimeError):
    """Raised by placeholder backends until GridLayoutBackend is wired."""


class NullLayoutBackend:
    """Stub backend used until B3 GridLayoutBackend is available."""

    def layout(self, design: Design, board: Board) -> Board:
        raise LayoutNotImplemented(
            "Layout backend not implemented. Use GridLayoutBackend "
            f"(design={design.id}, footprints={len(board.footprints)})."
        )


class LayoutPlanner:
    """Orchestrates schematic→board skeleton→backend place/route."""

    def __init__(self, backend: LayoutBackend | None = None) -> None:
        self.backend: LayoutBackend = backend or NullLayoutBackend()

    def run(self, design: Design, board: Board) -> Board:
        return self.backend.layout(design, board)


__all__ = [
    "LayoutBackend",
    "LayoutNotImplemented",
    "LayoutPlanner",
    "NullLayoutBackend",
]
