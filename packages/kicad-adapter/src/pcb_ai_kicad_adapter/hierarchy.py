"""Hierarchical / multi-sheet helpers for KiCad schematic ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcb_ai_kicad_adapter.parser import SExprNode


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


def symbol_instance_sheet_path(sym: SExprNode, *, default: str = "/") -> str:
    """Prefer the first `(instances … (path \"…\"))` entry; else `default`."""
    instances = sym.find("instances")
    if instances is None:
        return default
    for project in instances.find_all("project"):
        for path_node in project.find_all("path"):
            raw = path_node.atom_at(0)
            if raw is not None and raw != "":
                return raw
    return default


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
