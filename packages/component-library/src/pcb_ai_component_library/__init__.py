"""Curated component profiles for high-precision rules (20–30 parts target)."""

from pcb_ai_component_library.models import ComponentProfile
from pcb_ai_component_library.registry import get_by_mpn, list_by_class, load_all

__all__ = [
    "ComponentProfile",
    "get_by_mpn",
    "list_by_class",
    "load_all",
]
