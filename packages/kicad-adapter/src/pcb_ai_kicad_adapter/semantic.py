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


def uuid_fingerprint(design: Design) -> dict:
    """Stable map of component/net identity UUIDs for round-trip assertions.

    Component UUIDs are expected to survive KiCad → IR → emit → IR when emit
    preserves `Component.uuid`. Net UUIDs are deterministic seeds from connectivity
    (not KiCad wire UUIDs).
    """
    return {
        "components": sorted(
            [
                {
                    "reference": c.reference,
                    "uuid": c.uuid,
                    "sheet": (c.source_location.sheet if c.source_location else None),
                    "source_uuid": (c.source_location.uuid if c.source_location else None),
                }
                for c in design.components
            ],
            key=lambda row: (row["sheet"] or "", row["reference"]),
        ),
        "nets": sorted(
            [{"name": n.name, "uuid": n.uuid} for n in design.nets],
            key=lambda row: row["name"],
        ),
    }


def uuid_equal(a: Design, b: Design, *, include_nets: bool = True) -> bool:
    """True when component (and optionally net) UUID fingerprints match."""
    fa, fb = uuid_fingerprint(a), uuid_fingerprint(b)
    if fa["components"] != fb["components"]:
        return False
    if include_nets and fa["nets"] != fb["nets"]:
        return False
    return True


def collect_ast_uuids(ast) -> list[str]:
    """Collect every `(uuid …)` atom under an S-expression AST (order-stable DFS)."""
    found: list[str] = []

    def walk(node) -> None:
        if getattr(node, "is_atom", False):
            return
        if getattr(node, "head", None) == "uuid":
            atom = node.atom_at(0) if hasattr(node, "atom_at") else None
            if atom:
                found.append(atom)
            return
        for child in getattr(node, "children", []) or []:
            walk(child)

    walk(ast)
    return found


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
