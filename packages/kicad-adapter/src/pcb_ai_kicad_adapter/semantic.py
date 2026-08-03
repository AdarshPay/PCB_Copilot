"""Semantic comparison helpers for Circuit IR round-trip checks."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Component, Design, Net


def semantic_fingerprint(design: Design) -> dict:
    """Stable, UUID-agnostic summary of design connectivity semantics."""
    components = [_component_fp(c) for c in sorted(design.components, key=lambda c: c.reference)]
    nets = [_net_fp(n) for n in sorted(design.nets, key=lambda n: n.name)]
    return {
        "name": design.name,
        "source_tool": str(design.source_tool),
        "components": components,
        "nets": nets,
    }


def semantic_equal(a: Design, b: Design) -> bool:
    return semantic_fingerprint(a) == semantic_fingerprint(b)


def semantic_diff(a: Design, b: Design) -> dict:
    fa, fb = semantic_fingerprint(a), semantic_fingerprint(b)
    return {
        "equal": fa == fb,
        "a": fa,
        "b": fb,
    }


def _component_fp(c: Component) -> dict:
    return {
        "reference": c.reference,
        "value": c.value,
        "symbol_ref": c.symbol_ref,
        "footprint_ref": c.footprint_ref,
        "functional_class": str(c.functional_class),
        "pins": [
            {
                "number": p.number,
                "name": p.name,
                "electrical_role": str(p.electrical_role),
            }
            for p in sorted(c.pins, key=lambda p: p.number)
        ],
    }


def _net_fp(n: Net) -> dict:
    return {
        "name": n.name,
        "class": str(n.net_class),
        "endpoints": [
            {
                "component_ref": e.component_ref,
                "pin_number": e.pin_number,
            }
            for e in sorted(n.endpoints, key=lambda e: (e.component_ref, e.pin_number))
        ],
    }
