"""Component profile registry — load and query curated parts."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import FunctionalClass

from pcb_ai_component_library.models import ComponentProfile
from pcb_ai_component_library.profiles import ALL_PROFILES


def load_all() -> list[ComponentProfile]:
    """Return a copy of every curated component profile."""
    return list(ALL_PROFILES)


def get_by_mpn(mpn: str) -> ComponentProfile | None:
    """Look up a profile by orderable MPN (case-insensitive, stripped)."""
    key = mpn.strip().casefold()
    for profile in ALL_PROFILES:
        if profile.orderable_mpn.casefold() == key:
            return profile
    return None


def list_by_class(functional_class: FunctionalClass | str) -> list[ComponentProfile]:
    """Return profiles matching a functional class."""
    if isinstance(functional_class, str):
        target = FunctionalClass(functional_class)
    else:
        target = functional_class
    return [p for p in ALL_PROFILES if p.functional_class == target]


__all__ = ["get_by_mpn", "list_by_class", "load_all"]
