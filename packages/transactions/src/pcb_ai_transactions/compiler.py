"""Apply typed operations to a Design copy (prototype).

Guardrails
----------
* Production CAD mutation is forbidden. Operations compile into an in-memory IR
  snapshot; use ``compile_temp_branch`` for a temporary ``.kicad_sch`` under a
  dest directory. Human approval is still required before any production write.
* ``apply_operations`` always deep-copies the input Design; the caller's original
  is never mutated.
* Unsupported operation types raise ``TransactionError`` rather than silently
  skipping (except explicit ``noop``).
* Rollback metadata is enriched on apply where previous values are known so a
  later inverse pass can restore the prior IR state.
"""

from __future__ import annotations

from typing import Any

from pcb_ai_circuit_ir.models import (
    Component,
    Design,
    ElectricalRole,
    Endpoint,
    Net,
    NetClass,
    Operation,
)

# Operation types supported by the IR-level compiler (Phase A Day 60).
SUPPORTED_OPERATION_TYPES: frozenset[str] = frozenset(
    {
        "noop",
        "set_component_value",
        "set_footprint_ref",
        "set_component_attributes",
        "set_pin_electrical_role",
        "set_pin_voltage_domain",
        "add_component",
        "remove_component",
        "rename_component",
        "add_net",
        "set_net_class",
        "add_endpoint",
        "remove_endpoint",
    }
)


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
        _apply_one(result, op)
    return result


def _apply_one(result: Design, op: Operation) -> None:
    if op.type == "noop":
        return
    handler = _HANDLERS.get(op.type)
    if handler is None:
        raise TransactionError(f"Unsupported operation type {op.type!r}")
    handler(result, op)


def _find_component(design: Design, reference: str) -> Component:
    for component in design.components:
        if component.reference == reference:
            return component
    raise TransactionError(f"Unknown component target {reference!r}")


def _find_net(design: Design, name: str) -> Net:
    for net in design.nets:
        if net.name == name:
            return net
    raise TransactionError(f"Unknown net target {name!r}")


def _apply_set_component_value(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    if "previous_value" not in op.rollback:
        op.rollback = {**op.rollback, "previous_value": component.value}
    value = op.payload.get("value")
    component.value = value


def _apply_set_footprint_ref(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    if "footprint_ref" not in op.rollback:
        op.rollback = {**op.rollback, "footprint_ref": component.footprint_ref}
    footprint = op.payload.get("footprint_ref")
    component.footprint_ref = footprint


def _apply_set_component_attributes(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    attrs = op.payload.get("attributes") or {}
    if not isinstance(attrs, dict):
        raise TransactionError("set_component_attributes payload.attributes must be a dict")
    if "attributes" not in op.rollback:
        op.rollback = {
            **op.rollback,
            "attributes": {k: component.attributes.get(k) for k in attrs},
        }
    component.attributes.update(attrs)


def _apply_set_pin_electrical_role(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    pin_number = str(op.payload.get("pin_number", ""))
    role_raw = op.payload.get("electrical_role")
    if not pin_number or role_raw is None:
        raise TransactionError("set_pin_electrical_role requires pin_number and electrical_role")
    pin = next((p for p in component.pins if p.number == pin_number), None)
    if pin is None:
        raise TransactionError(f"Unknown pin {op.target}.{pin_number}")
    if "electrical_role" not in op.rollback:
        op.rollback = {
            **op.rollback,
            "pin_number": pin_number,
            "electrical_role": pin.electrical_role.value,
        }
    pin.electrical_role = ElectricalRole(role_raw)


def _apply_set_pin_voltage_domain(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    pin_number = str(op.payload.get("pin_number", ""))
    if not pin_number:
        raise TransactionError("set_pin_voltage_domain requires pin_number")
    pin = next((p for p in component.pins if p.number == pin_number), None)
    if pin is None:
        raise TransactionError(f"Unknown pin {op.target}.{pin_number}")
    if "voltage_domain" not in op.rollback:
        op.rollback = {
            **op.rollback,
            "pin_number": pin_number,
            "voltage_domain": pin.voltage_domain,
        }
    pin.voltage_domain = op.payload.get("voltage_domain")


def _component_from_payload(payload: dict[str, Any]) -> Component:
    raw = payload.get("component")
    if raw is None:
        raise TransactionError("add_component requires payload.component")
    if isinstance(raw, Component):
        return raw.model_copy(deep=True)
    if not isinstance(raw, dict):
        raise TransactionError("add_component payload.component must be a dict or Component")
    return Component.model_validate(raw)


def _apply_add_component(design: Design, op: Operation) -> None:
    component = _component_from_payload(op.payload)
    if any(c.reference == component.reference for c in design.components):
        raise TransactionError(f"Component {component.reference!r} already exists")
    if "remove_reference" not in op.rollback:
        op.rollback = {**op.rollback, "remove_reference": component.reference}
    design.components.append(component)


def _apply_remove_component(design: Design, op: Operation) -> None:
    component = _find_component(design, op.target)
    if "component" not in op.rollback:
        op.rollback = {**op.rollback, "component": component.model_dump(mode="json", by_alias=True)}
    design.components = [c for c in design.components if c.reference != op.target]
    # Drop endpoints that referenced the removed part.
    for net in design.nets:
        net.endpoints = [ep for ep in net.endpoints if ep.component_ref != op.target]


def _apply_rename_component(design: Design, op: Operation) -> None:
    new_ref = op.payload.get("new_reference")
    if not new_ref or not isinstance(new_ref, str):
        raise TransactionError("rename_component requires payload.new_reference")
    uuid_filter = op.payload.get("uuid")
    matches = [c for c in design.components if c.reference == op.target]
    if not matches:
        raise TransactionError(f"Unknown component target {op.target!r}")
    if uuid_filter:
        matches = [c for c in matches if c.uuid == uuid_filter]
        if not matches:
            raise TransactionError(f"No component {op.target!r} with uuid {uuid_filter!r}")
    if any(c.reference == new_ref for c in design.components):
        raise TransactionError(f"Component {new_ref!r} already exists")
    victim = matches[-1]
    if "old_reference" not in op.rollback:
        op.rollback = {**op.rollback, "old_reference": op.target, "uuid": victim.uuid}
    old_ref = victim.reference
    same_ref_count = sum(1 for c in design.components if c.reference == old_ref)
    victim.reference = new_ref
    # Unique rename: retarget endpoints. Duplicate-ref remediations leave nets on the
    # kept designator (injected clones are typically unconnected).
    if same_ref_count == 1:
        for net in design.nets:
            for ep in net.endpoints:
                if ep.component_ref == old_ref:
                    ep.component_ref = new_ref


def _apply_add_net(design: Design, op: Operation) -> None:
    raw = op.payload.get("net")
    if raw is None:
        raise TransactionError("add_net requires payload.net")
    net = raw.model_copy(deep=True) if isinstance(raw, Net) else Net.model_validate(raw)
    if any(n.name == net.name for n in design.nets):
        raise TransactionError(f"Net {net.name!r} already exists")
    if "remove_net" not in op.rollback:
        op.rollback = {**op.rollback, "remove_net": net.name}
    design.nets.append(net)


def _apply_set_net_class(design: Design, op: Operation) -> None:
    net = _find_net(design, op.target)
    class_raw = op.payload.get("net_class")
    if class_raw is None:
        raise TransactionError("set_net_class requires payload.net_class")
    if "net_class" not in op.rollback:
        op.rollback = {**op.rollback, "net_class": net.net_class.value}
    net.net_class = NetClass(class_raw)


def _apply_add_endpoint(design: Design, op: Operation) -> None:
    net = _find_net(design, op.target)
    ref = op.payload.get("component_ref")
    pin_number = op.payload.get("pin_number")
    if not ref or not pin_number:
        raise TransactionError("add_endpoint requires component_ref and pin_number")
    ref_s = str(ref)
    pin_s = str(pin_number)
    # Ensure the component/pin exist.
    component = _find_component(design, ref_s)
    if not any(p.number == pin_s for p in component.pins):
        raise TransactionError(f"Unknown pin {ref_s}.{pin_s}")
    if any(ep.component_ref == ref_s and ep.pin_number == pin_s for ep in net.endpoints):
        return  # idempotent
    if "component_ref" not in op.rollback:
        op.rollback = {**op.rollback, "component_ref": ref_s, "pin_number": pin_s}
    net.endpoints.append(
        Endpoint(
            component_ref=ref_s,
            pin_number=pin_s,
            pin_name=op.payload.get("pin_name"),
        )
    )


def _apply_remove_endpoint(design: Design, op: Operation) -> None:
    net = _find_net(design, op.target)
    ref = op.payload.get("component_ref")
    pin_number = op.payload.get("pin_number")
    if not ref or not pin_number:
        raise TransactionError("remove_endpoint requires component_ref and pin_number")
    ref_s = str(ref)
    pin_s = str(pin_number)
    remaining: list[Endpoint] = []
    removed: Endpoint | None = None
    for ep in net.endpoints:
        if removed is None and ep.component_ref == ref_s and ep.pin_number == pin_s:
            removed = ep
            continue
        remaining.append(ep)
    if removed is None:
        raise TransactionError(f"Endpoint {ref_s}.{pin_s} not on net {op.target!r}")
    if "component_ref" not in op.rollback:
        op.rollback = {
            **op.rollback,
            "component_ref": ref_s,
            "pin_number": pin_s,
            "pin_name": removed.pin_name,
        }
    net.endpoints = remaining


_HANDLERS = {
    "set_component_value": _apply_set_component_value,
    "set_footprint_ref": _apply_set_footprint_ref,
    "set_component_attributes": _apply_set_component_attributes,
    "set_pin_electrical_role": _apply_set_pin_electrical_role,
    "set_pin_voltage_domain": _apply_set_pin_voltage_domain,
    "add_component": _apply_add_component,
    "remove_component": _apply_remove_component,
    "rename_component": _apply_rename_component,
    "add_net": _apply_add_net,
    "set_net_class": _apply_set_net_class,
    "add_endpoint": _apply_add_endpoint,
    "remove_endpoint": _apply_remove_endpoint,
}


def semantic_diff(before: Design, after: Design) -> dict[str, Any]:
    """Shallow component/net change summary for review artifacts."""
    before_refs = {c.reference: c for c in before.components}
    after_refs = {c.reference: c for c in after.components}
    added_components = sorted(set(after_refs) - set(before_refs))
    removed_components = sorted(set(before_refs) - set(after_refs))
    changed_components = [
        ref
        for ref in sorted(set(before_refs) & set(after_refs))
        if before_refs[ref] != after_refs[ref]
    ]
    before_nets = {n.name: n for n in before.nets}
    after_nets = {n.name: n for n in after.nets}
    added_nets = sorted(set(after_nets) - set(before_nets))
    removed_nets = sorted(set(before_nets) - set(after_nets))
    changed_nets = [
        name
        for name in sorted(set(before_nets) & set(after_nets))
        if before_nets[name] != after_nets[name]
    ]
    return {
        "changed_components": sorted(changed_components + added_components + removed_components),
        "changed_nets": sorted(changed_nets + added_nets + removed_nets),
        "added_components": added_components,
        "removed_components": removed_components,
        "added_nets": added_nets,
        "removed_nets": removed_nets,
        "before_revision": before.revision,
        "after_revision": after.revision,
    }


def export_branch_diff(
    before: Design,
    after: Design,
    *,
    operations: list[Operation] | None = None,
    branch_name: str = "temp",
) -> dict[str, Any]:
    """Semantic before/after summary for a temp-branch review artifact.

    Explicitly records that production CAD was not mutated. Pair with
    ``compile_temp_branch`` when a temporary ``.kicad_sch`` artifact is needed;
    human approval is still required before any production write.
    """
    diff = semantic_diff(before, after)
    ops = list(operations or [])
    return {
        **diff,
        "branch": branch_name,
        "production_mutation": False,
        "operations_applied": [
            {"id": op.id, "type": op.type, "target": op.target, "risk_tier": op.risk_tier.value}
            for op in ops
        ],
        "operation_count": len(ops),
        "design_id": before.id,
    }
