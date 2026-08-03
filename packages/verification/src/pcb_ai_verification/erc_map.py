"""Map KiCad ERC affected items back to Circuit IR source objects."""

from __future__ import annotations

import re
from typing import Any

# "R1 Pin 1 [...]", "Symbol R1 Pin 1", "Pin R1-1"
_REF_PIN = re.compile(
    r"(?:Symbol\s+)?(?P<ref>[A-Za-z]+[#A-Za-z]*\d*)\s+Pin\s+(?P<pin>[^\s,\]]+)",
    re.IGNORECASE,
)
_REF_ONLY = re.compile(
    r"(?:Symbol|Component)\s+(?P<ref>[A-Za-z]+[#A-Za-z]*\d*)\b",
    re.IGNORECASE,
)


def collect_objects_from_items(
    items: list[Any],
    *,
    design: Any | None = None,
    sheet_path: str | None = None,
) -> list[str]:
    """Build Finding.objects from ERC item payloads, preferring IR refs/UUIDs."""
    uuid_index, ref_index = _design_indexes(design)
    objects: list[str] = []
    seen: set[str] = set()

    def add(value: str | None) -> None:
        if not value:
            return
        if value in seen:
            return
        seen.add(value)
        objects.append(value)

    if sheet_path and sheet_path not in {"/", ""}:
        add(f"sheet:{sheet_path}")

    for item in items:
        if not isinstance(item, dict):
            if isinstance(item, str) and item.strip():
                add(item.strip())
            continue

        item_uuid = item.get("uuid")
        if isinstance(item_uuid, str) and item_uuid:
            add(item_uuid)
            mapped = uuid_index.get(item_uuid)
            if mapped:
                add(mapped)

        description = str(item.get("description") or "")
        ref, pin = _parse_ref_pin(description)
        if ref:
            add(ref)
            if pin:
                add(f"{ref}.{pin}")
            # Prefer IR component UUID when description names a known reference.
            if ref in ref_index:
                add(ref_index[ref])

        if not item_uuid and not ref and description.strip():
            add(description.strip())

    return objects


def attach_design_objects(findings: list[Any], design: Any) -> list[Any]:
    """Re-map Finding.objects using a Design after parse-time mapping was skipped."""
    from pcb_ai_circuit_ir.models import Finding

    remapped: list[Finding] = []
    for finding in findings:
        # Reconstruct minimal item list from existing UUID-looking objects + explanation.
        synthetic_items: list[dict[str, Any]] = []
        for obj in finding.objects:
            if _looks_like_uuid(obj):
                synthetic_items.append({"uuid": obj, "description": ""})
            elif "." in obj and not obj.startswith("sheet:"):
                ref, _, pin = obj.partition(".")
                synthetic_items.append({"description": f"{ref} Pin {pin}"})
            elif not obj.startswith("sheet:"):
                synthetic_items.append({"description": f"Symbol {obj}"})
        objects = collect_objects_from_items(synthetic_items, design=design)
        # Preserve any sheet: markers and unexplained strings.
        for obj in finding.objects:
            if obj.startswith("sheet:") and obj not in objects:
                objects.insert(0, obj)
        remapped.append(finding.model_copy(update={"objects": objects}))
    return remapped


def _design_indexes(design: Any | None) -> tuple[dict[str, str], dict[str, str]]:
    """Return (uuid -> reference, reference -> uuid) from a Design."""
    uuid_to_ref: dict[str, str] = {}
    ref_to_uuid: dict[str, str] = {}
    if design is None:
        return uuid_to_ref, ref_to_uuid
    for component in getattr(design, "components", []) or []:
        ref = getattr(component, "reference", None)
        uuid = getattr(component, "uuid", None)
        if ref and uuid:
            ref_to_uuid[str(ref)] = str(uuid)
            uuid_to_ref[str(uuid)] = str(ref)
        loc = getattr(component, "source_location", None)
        loc_uuid = getattr(loc, "uuid", None) if loc is not None else None
        if loc_uuid and ref:
            uuid_to_ref[str(loc_uuid)] = str(ref)
    for net in getattr(design, "nets", []) or []:
        name = getattr(net, "name", None)
        uuid = getattr(net, "uuid", None)
        if name and uuid:
            uuid_to_ref[str(uuid)] = str(name)
            ref_to_uuid[str(name)] = str(uuid)
    return uuid_to_ref, ref_to_uuid


def _parse_ref_pin(description: str) -> tuple[str | None, str | None]:
    match = _REF_PIN.search(description)
    if match:
        return match.group("ref"), match.group("pin").rstrip(",]")
    match = _REF_ONLY.search(description)
    if match:
        return match.group("ref"), None
    return None, None


def _looks_like_uuid(value: str) -> bool:
    parts = value.split("-")
    return len(parts) == 5 and all(parts)
