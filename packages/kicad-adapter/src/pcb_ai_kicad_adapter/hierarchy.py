"""Hierarchical / multi-sheet helpers for KiCad schematic ingest."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pcb_ai_kicad_adapter.parser import SExprNode

# Vector bus: DATA[7..0] → DATA7 … DATA0
_BUS_VECTOR = re.compile(r"^(.+)\[(\d+)\.\.(\d+)\]$")
# Group bus: {A B C} or MEM{WE OE} → A,B,C or MEMWE,MEMOE
_BUS_GROUP = re.compile(r"^([^{]*)\{([^}]+)\}$")


@dataclass
class SheetRef:
    """A `(sheet …)` symbol on a parent schematic referencing a child file."""

    uuid: str
    name: str | None
    filename: str
    pin_names: list[str] = field(default_factory=list)
    pin_points: dict[str, tuple[float, float]] = field(default_factory=dict)
    pin_uuids: dict[str, str | None] = field(default_factory=dict)


def child_sheet_path(parent_path: str, sheet_uuid: str) -> str:
    """Build KiCad-style sheet path for a child under `parent_path`."""
    if parent_path in ("", "/"):
        return f"/{sheet_uuid}"
    return f"{parent_path.rstrip('/')}/{sheet_uuid}"


def extract_sheet_refs(root: SExprNode) -> list[SheetRef]:
    """Collect hierarchical sheet symbols from a schematic root."""
    refs: list[SheetRef] = []
    for sheet in root.find_all("sheet"):
        props = _properties(sheet)
        filename = props.get("Sheetfile") or props.get("Sheet file")
        if not filename:
            continue
        uuid = _first_atom(sheet.find("uuid"))
        if not uuid:
            continue
        pin_names: list[str] = []
        pin_points: dict[str, tuple[float, float]] = {}
        pin_uuids: dict[str, str | None] = {}
        for pin in sheet.find_all("pin"):
            name = pin.atom_at(0)
            if not name:
                continue
            pin_names.append(name)
            at = pin.find("at")
            if at is not None:
                try:
                    x = float(at.atom_at(0) or 0)
                    y = float(at.atom_at(1) or 0)
                    pin_points[name] = (x, y)
                except ValueError:
                    pass
            pin_uuids[name] = _first_atom(pin.find("uuid"))
        refs.append(
            SheetRef(
                uuid=uuid,
                name=props.get("Sheetname") or props.get("Sheet name"),
                filename=filename,
                pin_names=pin_names,
                pin_points=pin_points,
                pin_uuids=pin_uuids,
            )
        )
    return refs


def resolve_child_path(parent_file: Path, sheet_filename: str) -> Path:
    """Resolve a Sheetfile property relative to the parent schematic path."""
    child = Path(sheet_filename)
    if child.is_absolute():
        return child
    return (parent_file.parent / child).resolve()


def symbol_instance_paths(sym: SExprNode) -> list[tuple[str, str | None]]:
    """Return `(sheet_path, reference)` pairs from `(instances …)`."""
    instances = sym.find("instances")
    if instances is None:
        return []
    out: list[tuple[str, str | None]] = []
    for project in instances.find_all("project"):
        for path_node in project.find_all("path"):
            raw = path_node.atom_at(0)
            if raw is None or raw == "":
                continue
            ref = None
            for child in path_node.children:
                if isinstance(child, SExprNode) and not child.is_atom and child.head == "reference":
                    ref = child.atom_at(0)
                    break
            out.append((raw, ref))
    return out


def symbol_instance_sheet_path(
    sym: SExprNode,
    *,
    default: str = "/",
    preferred: str | None = None,
) -> str:
    """Resolve instance sheet path.

    When `preferred` is set (current hierarchy visit path), match that entry.
    Otherwise prefer the first `(instances … (path \"…\"))` entry; else `default`.
    """
    paths = symbol_instance_paths(sym)
    if preferred is not None:
        for path, _ref in paths:
            if path == preferred:
                return path
        # Prefix match: preferred "/uuid" vs stored "/uuid/…" is uncommon; exact only.
    if paths:
        return paths[0][0]
    return default


def symbol_instance_reference(
    sym: SExprNode,
    *,
    sheet_path: str,
    fallback: str | None,
) -> str | None:
    """Prefer `(instances … (path sheet_path (reference …)))` over property Reference."""
    for path, ref in symbol_instance_paths(sym):
        if path == sheet_path and ref:
            return ref
    return fallback


def expand_bus_members(label: str) -> list[str] | None:
    """Expand a KiCad bus label into member net names, or None if not a bus label.

    Supports vector form ``NAME[M..N]`` (members ``NAMEk``) and group form
    ``{A B}`` / ``PRE{A B}`` (members ``A``, ``B`` or ``PREA``, ``PREB``).
    """
    m = _BUS_VECTOR.match(label)
    if m:
        prefix, a_s, b_s = m.group(1), m.group(2), m.group(3)
        a, b = int(a_s), int(b_s)
        if a >= b:
            indices = range(a, b - 1, -1)
        else:
            indices = range(a, b + 1)
        return [f"{prefix}{i}" for i in indices]

    m = _BUS_GROUP.match(label)
    if m:
        prefix, body = m.group(1), m.group(2)
        parts = [p for p in body.replace(",", " ").split() if p]
        if not parts:
            return None
        return [f"{prefix}{p}" for p in parts]

    return None


def is_bus_label(name: str) -> bool:
    """True when `name` is a vector or group bus label."""
    return expand_bus_members(name) is not None


def root_sheet_instances_paths(root: SExprNode) -> list[str]:
    """Paths listed under `(sheet_instances …)`."""
    block = root.find("sheet_instances")
    if block is None:
        return []
    return [p.atom_at(0) or "/" for p in block.find_all("path")]


def _properties(node: SExprNode) -> dict[str, str]:
    props: dict[str, str] = {}
    for prop in node.find_all("property"):
        key = prop.atom_at(0)
        val = prop.atom_at(1)
        if key is not None and val is not None:
            props[key] = val
    return props


def _first_atom(node: SExprNode | None) -> str | None:
    if node is None:
        return None
    return node.atom_at(0)
