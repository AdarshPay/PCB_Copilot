"""Apply typed operations to a Design copy (prototype).

Production CAD mutation is forbidden. Operations compile into a temporary
branch only after human approval (see implementation plan §2).
"""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design, Operation


class TransactionError(ValueError):
    pass


class TransactionCompiler:
    """Compile reversible operations against an IR snapshot."""

    def compile(self, design: Design, operations: list[Operation]) -> Design:
        return apply_operations(design, operations)


def apply_operations(design: Design, operations: list[Operation]) -> Design:
    """Return a deep-copied Design with supported operations applied."""
    result = design.model_copy(deep=True)
    for op in operations:
        if op.type == "noop":
            continue
        if op.type == "set_component_value":
            ref = op.target
            value = op.payload.get("value")
            matched = False
            for component in result.components:
                if component.reference == ref:
                    component.value = value
                    matched = True
                    break
            if not matched:
                raise TransactionError(f"Unknown component target {ref!r}")
            continue
        raise TransactionError(f"Unsupported operation type {op.type!r}")
    return result


def semantic_diff(before: Design, after: Design) -> dict:
    """Shallow component/net change summary for review artifacts."""
    before_refs = {c.reference: c for c in before.components}
    after_refs = {c.reference: c for c in after.components}
    changed_components = [
        ref
        for ref in sorted(set(before_refs) | set(after_refs))
        if before_refs.get(ref) != after_refs.get(ref)
    ]
    before_nets = {n.name: n for n in before.nets}
    after_nets = {n.name: n for n in after.nets}
    changed_nets = [
        name
        for name in sorted(set(before_nets) | set(after_nets))
        if before_nets.get(name) != after_nets.get(name)
    ]
    return {
        "changed_components": changed_components,
        "changed_nets": changed_nets,
        "before_revision": before.revision,
        "after_revision": after.revision,
    }
