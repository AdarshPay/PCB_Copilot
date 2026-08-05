"""Normalize KiCad schematic AST into Circuit IR."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid5, UUID

from pcb_ai_circuit_ir.models import (
    Block,
    Component,
    Constraint,
    Design,
    ElectricalRole,
    Endpoint,
    FunctionalClass,
    Net,
    NetClass,
    Pin,
    SourceLocation,
    SourceTool,
)
from pcb_ai_kicad_adapter.connectivity import (
    ConnectivityGraph,
    LabelAttachment,
    PinAttachment,
    Point,
    qpoint,
)
from pcb_ai_kicad_adapter.hierarchy import (
    SheetRef,
    child_sheet_path,
    expand_bus_members,
    extract_sheet_refs,
    is_bus_label,
    resolve_child_path,
    symbol_instance_reference,
)
from pcb_ai_kicad_adapter.parser import SExprNode, parse_schematic_sexpr

# Stable namespace for deterministic net UUIDs derived from schematic content.
_NET_NS = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class _SheetNetFragment:
    """One geometric net group on a single sheet, before hierarchy merge."""

    sheet_path: str
    endpoints: list[Endpoint]
    labels: list[LabelAttachment]
    name_hint: str | None = None
    is_bus: bool = False
    bus_members: list[str] = field(default_factory=list)
    bus_name: str | None = None  # member net → parent bus label name



@dataclass
class _HierarchyBridge:
    """Links a parent sheet pin net to a child hierarchical_label net by name."""

    parent_sheet_path: str
    child_sheet_path: str
    pin_name: str
    pin_point: tuple[float, float] | None = None


@dataclass
class _SheetNormalizeResult:
    sheet_path: str
    sheet_uuid: str | None
    sheet_name: str | None
    file_path: str | None
    version: str | None
    title: str | None
    components: list[Component] = field(default_factory=list)
    fragments: list[_SheetNetFragment] = field(default_factory=list)
    sheet_refs: list[SheetRef] = field(default_factory=list)


class NormalizationError(ValueError):
    pass


_PIN_TYPE_MAP: dict[str, ElectricalRole] = {
    "input": ElectricalRole.DIGITAL_IN,
    "output": ElectricalRole.DIGITAL_OUT,
    "bidirectional": ElectricalRole.DIGITAL_BIDIR,
    "tri_state": ElectricalRole.DIGITAL_BIDIR,
    "passive": ElectricalRole.PASSIVE,
    "free": ElectricalRole.UNSPECIFIED,
    "unspecified": ElectricalRole.UNSPECIFIED,
    "power_in": ElectricalRole.POWER_IN,
    "power_out": ElectricalRole.POWER_OUT,
    "open_collector": ElectricalRole.OPEN_DRAIN,
    "open_emitter": ElectricalRole.DIGITAL_OUT,
    "no_connect": ElectricalRole.NO_CONNECT,
}

_REF_CLASS: list[tuple[re.Pattern[str], FunctionalClass]] = [
    (re.compile(r"^U\d*", re.I), FunctionalClass.MCU),
    (re.compile(r"^J\d*", re.I), FunctionalClass.CONNECTOR),
    (re.compile(r"^P\d*", re.I), FunctionalClass.CONNECTOR),
    (re.compile(r"^R\d*", re.I), FunctionalClass.PASSIVE),
    (re.compile(r"^C\d*", re.I), FunctionalClass.PASSIVE),
    (re.compile(r"^L\d*", re.I), FunctionalClass.PASSIVE),
    (re.compile(r"^D\d*", re.I), FunctionalClass.PROTECTION),
    (re.compile(r"^Q\d*", re.I), FunctionalClass.OTHER),
    (re.compile(r"^#PWR", re.I), FunctionalClass.OTHER),
    (re.compile(r"^#FLG", re.I), FunctionalClass.OTHER),
]


def normalize_to_circuit_ir(
    ast: SExprNode | Design,
    *,
    design_id: str | None = None,
    sheet_path: str = "/",
    file_path: str | Path | None = None,
) -> Design:
    """Convert a parsed schematic AST into a typed Design.

    If a Design is passed through (e.g. golden fixtures), it is returned as-is.
    Single-sheet ASTs are normalized with `sheet_path` (default `/`).
    Prefer `ingest_schematic` for on-disk projects so child sheets are loaded.
    """
    if isinstance(ast, Design):
        return ast
    if ast.head != "kicad_sch":
        raise NormalizationError(f"Expected kicad_sch root, got {ast.head!r}")
    result = _normalize_sheet(
        ast,
        sheet_path=sheet_path,
        file_path=str(file_path) if file_path is not None else None,
    )
    return _design_from_sheets([result], bridges=[], design_id=design_id)


def ingest_schematic(
    source: str | Path,
    *,
    design_id: str | None = None,
) -> Design:
    """Parse a `.kicad_sch` path or text and normalize to Circuit IR.

    When `source` is an on-disk schematic, child sheets referenced by `(sheet …)`
    / Sheetfile are loaded recursively and merged (global labels, power nets,
    and hierarchical sheet-pin ↔ hierarchical_label bridges).
    """
    path: Path | None = None
    if isinstance(source, Path):
        path = source
        default_id = design_id or f"kicad.{source.stem}"
    elif isinstance(source, str) and "\n" not in source and source.endswith(".kicad_sch"):
        candidate = Path(source)
        if candidate.is_file():
            path = candidate
            default_id = design_id or f"kicad.{candidate.stem}"
        else:
            ast = parse_schematic_sexpr(source)
            return normalize_to_circuit_ir(ast, design_id=design_id or "kicad.inline")
    else:
        ast = parse_schematic_sexpr(source)
        return normalize_to_circuit_ir(ast, design_id=design_id or "kicad.inline")

    assert path is not None
    return _ingest_hierarchy(path.resolve(), design_id=default_id)


def _ingest_hierarchy(root_path: Path, *, design_id: str) -> Design:
    sheets: list[_SheetNormalizeResult] = []
    bridges: list[_HierarchyBridge] = []
    # Allow the same Sheetfile to be instantiated under multiple sheet paths.
    # Detect true cycles via the active sheet-path stack (not by file path).
    active_paths: set[str] = set()
    seen_instances: set[str] = set()
    ast_cache: dict[Path, SExprNode] = {}

    def visit(file_path: Path, sheet_path: str) -> _SheetNormalizeResult:
        resolved = file_path.resolve()
        if sheet_path in active_paths:
            raise NormalizationError(
                f"Hierarchical sheet cycle involving path {sheet_path!r} "
                f"(file {resolved})"
            )
        if sheet_path in seen_instances:
            raise NormalizationError(
                f"Duplicate sheet instance path {sheet_path!r} (file {resolved})"
            )
        active_paths.add(sheet_path)
        seen_instances.add(sheet_path)
        try:
            if resolved not in ast_cache:
                ast_cache[resolved] = parse_schematic_sexpr(resolved)
            ast = ast_cache[resolved]
            result = _normalize_sheet(ast, sheet_path=sheet_path, file_path=str(resolved))
            sheets.append(result)
            for ref in result.sheet_refs:
                child_path = child_sheet_path(sheet_path, ref.uuid)
                child_file = resolve_child_path(resolved, ref.filename)
                if not child_file.is_file():
                    raise NormalizationError(
                        f"Missing child schematic {ref.filename!r} "
                        f"(resolved {child_file}) referenced from {resolved}"
                    )
                for pin_name in ref.pin_names:
                    bridges.append(
                        _HierarchyBridge(
                            parent_sheet_path=sheet_path,
                            child_sheet_path=child_path,
                            pin_name=pin_name,
                            pin_point=ref.pin_points.get(pin_name),
                        )
                    )
                visit(child_file, child_path)
            return result
        finally:
            active_paths.discard(sheet_path)

    visit(root_path, "/")
    return _design_from_sheets(sheets, bridges=bridges, design_id=design_id)


def _normalize_sheet(
    root: SExprNode,
    *,
    sheet_path: str,
    file_path: str | None,
) -> _SheetNormalizeResult:
    version = _first_atom(root.find("version"))
    sheet_uuid = _first_atom(root.find("uuid"))
    title = _title_block_name(root)
    sheet_refs = extract_sheet_refs(root)

    lib_pins = _index_lib_symbol_pins(root.find("lib_symbols"))
    components: list[Component] = []
    # Wire connectivity is separate from bus connectivity: bus_entry associates
    # them by name/membership without electrically shorting all members together.
    wire_graph = ConnectivityGraph()
    bus_graph = ConnectivityGraph()
    instance_pin_points: list[tuple[Component, list[PinAttachment]]] = []

    for sym in root.find_all("symbol"):
        # Skip nested library definitions accidentally present under root.
        if sym.find("lib_id") is None and sym.find("pin") is None:
            continue
        component, attachments = _symbol_instance_to_component(
            sym,
            lib_pins,
            sheet_path=sheet_path,
            file_path=file_path,
        )
        if component is None:
            continue
        components.append(component)
        instance_pin_points.append((component, attachments))
        for att in attachments:
            wire_graph.add_pin(att)

    for wire in root.find_all("wire"):
        pts = _wire_points(wire)
        uuid = _first_atom(wire.find("uuid"))
        for i in range(len(pts) - 1):
            wire_graph.add_wire(pts[i], pts[i + 1], uuid=uuid)

    for poly in root.find_all("polyline"):
        # Graphical polylines are not electrical buses; keep legacy wire treatment.
        pts = _polyline_points(poly)
        uuid = _first_atom(poly.find("uuid"))
        for i in range(len(pts) - 1):
            wire_graph.add_wire(pts[i], pts[i + 1], uuid=uuid)

    for bus in root.find_all("bus"):
        pts = _wire_points(bus)
        uuid = _first_atom(bus.find("uuid"))
        for i in range(len(pts) - 1):
            bus_graph.add_wire(pts[i], pts[i + 1], uuid=uuid)

    bus_entries: list[tuple[Point, Point]] = []
    for entry in root.find_all("bus_entry"):
        ends = _bus_entry_points(entry)
        if ends is None:
            continue
        a, b = ends
        # Endpoints participate so labels/wires can attach; association is
        # recorded separately (no cross-graph UF union of members).
        wire_graph.add_junction(a)
        wire_graph.add_junction(b)
        bus_graph.add_junction(a)
        bus_graph.add_junction(b)
        bus_entries.append((a, b))

    for jn in root.find_all("junction"):
        at = jn.find("at")
        if at is not None:
            pt = _at_point(at)
            if pt is not None:
                wire_graph.add_junction(pt)

    for label in root.find_all("label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                att = LabelAttachment(
                    name=name,
                    point=pt,
                    scope="local",
                    uuid=_first_atom(label.find("uuid")),
                )
                if is_bus_label(name):
                    bus_graph.add_label(att)
                else:
                    wire_graph.add_label(att)

    for label in root.find_all("global_label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                att = LabelAttachment(
                    name=name,
                    point=pt,
                    scope="global",
                    uuid=_first_atom(label.find("uuid")),
                )
                if is_bus_label(name):
                    bus_graph.add_label(att)
                else:
                    wire_graph.add_label(att)

    for label in root.find_all("hierarchical_label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                wire_graph.add_label(
                    LabelAttachment(
                        name=name,
                        point=pt,
                        scope="hierarchical",
                        uuid=_first_atom(label.find("uuid")),
                    )
                )

    # Sheet pins on the parent: attach hierarchical labels at pin coordinates
    # so parent-side wiring joins the bridge by pin name.
    for ref in sheet_refs:
        for pin_name, (px, py) in ref.pin_points.items():
            wire_graph.add_label(
                LabelAttachment(
                    name=pin_name,
                    point=qpoint(px, py),
                    scope="hierarchical",
                    uuid=ref.pin_uuids.get(pin_name),
                )
            )

    # Power-symbol net naming: Value property is the global net name.
    for component, attachments in instance_pin_points:
        if component.reference.startswith("#PWR") or component.attributes.get("power_symbol"):
            net_name = component.value or component.reference
            for att in attachments:
                wire_graph.add_label(
                    LabelAttachment(
                        name=net_name,
                        point=att.point,
                        scope="global",
                        uuid=component.uuid,
                    )
                )

    fragments: list[_SheetNetFragment] = []
    fragments.extend(_fragments_from_graph(wire_graph, sheet_path=sheet_path, is_bus=False))
    fragments.extend(_fragments_from_graph(bus_graph, sheet_path=sheet_path, is_bus=True))
    _annotate_bus_entry_membership(fragments, bus_entries, wire_graph, bus_graph)

    return _SheetNormalizeResult(
        sheet_path=sheet_path,
        sheet_uuid=sheet_uuid,
        sheet_name=title,
        file_path=file_path,
        version=version,
        title=title,
        components=components,
        fragments=fragments,
        sheet_refs=sheet_refs,
    )


def _design_from_sheets(
    sheets: list[_SheetNormalizeResult],
    *,
    bridges: list[_HierarchyBridge],
    design_id: str | None,
) -> Design:
    if not sheets:
        raise NormalizationError("No schematic sheets to normalize")

    root = sheets[0]
    components = [c for s in sheets for c in s.components]
    _qualify_reused_symbol_uuids(components)
    all_fragments = [f for s in sheets for f in s.fragments]
    nets = _merge_hierarchy_nets(
        all_fragments,
        bridges=bridges,
        design_id=design_id or root.sheet_uuid or "kicad",
    )

    blocks = [
        Block(
            id=s.sheet_uuid or s.sheet_path,
            name=s.sheet_name or s.sheet_path,
            description=f"sheet_path={s.sheet_path}"
            + (f"; file={s.file_path}" if s.file_path else ""),
            component_refs=[c.reference for c in s.components],
        )
        for s in sheets
    ]

    return Design(
        id=design_id or (f"kicad.{root.sheet_uuid}" if root.sheet_uuid else "kicad.unknown"),
        source_tool=SourceTool.KICAD,
        source_version=root.version,
        revision="0",
        name=root.title,
        blocks=blocks,
        components=components,
        nets=nets,
    )


class _FragmentUF:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _merge_hierarchy_nets(
    fragments: list[_SheetNetFragment],
    *,
    bridges: list[_HierarchyBridge],
    design_id: str,
) -> list[Net]:
    if not fragments:
        return []

    uf = _FragmentUF(len(fragments))

    # Global / power labels with the same name merge across sheets.
    global_index: dict[str, int] = {}
    for i, frag in enumerate(fragments):
        for lb in frag.labels:
            if lb.scope != "global":
                continue
            prev = global_index.get(lb.name)
            if prev is None:
                global_index[lb.name] = i
            else:
                uf.union(prev, i)

    # Hierarchical sheet-pin ↔ child hierarchical_label bridges.
    # Parent hits are scoped to the specific sheet-pin point so multiple
    # same-named pins on one parent (shared-sheet reuse) do not collapse.
    def _hier_index(
        sheet_path: str,
        name: str,
        *,
        point: tuple[float, float] | None = None,
    ) -> list[int]:
        hits: list[int] = []
        target = qpoint(point[0], point[1]) if point is not None else None
        for i, frag in enumerate(fragments):
            if frag.sheet_path != sheet_path:
                continue
            for lb in frag.labels:
                if lb.scope != "hierarchical" or lb.name != name:
                    continue
                if target is not None and lb.point != target:
                    continue
                hits.append(i)
                break
        return hits

    for bridge in bridges:
        parent_hits = _hier_index(
            bridge.parent_sheet_path,
            bridge.pin_name,
            point=bridge.pin_point,
        )
        child_hits = _hier_index(bridge.child_sheet_path, bridge.pin_name)
        for p in parent_hits:
            for c in child_hits:
                uf.union(p, c)

    groups: dict[int, list[int]] = {}
    for i in range(len(fragments)):
        groups.setdefault(uf.find(i), []).append(i)

    nets: list[Net] = []
    anonymous_i = 0
    for members in groups.values():
        frags = [fragments[i] for i in members]
        labels = [lb for f in frags for lb in f.labels]
        endpoints = [ep for f in frags for ep in f.endpoints]
        seen: set[tuple[str, str]] = set()
        uniq: list[Endpoint] = []
        for ep in sorted(endpoints, key=lambda e: (e.component_ref, e.pin_number)):
            key = (ep.component_ref, ep.pin_number)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(ep)

        name = _choose_net_name(labels, [])
        if name is None:
            for f in frags:
                if f.name_hint:
                    name = f.name_hint
                    break
        if name is None:
            anonymous_i += 1
            if uniq:
                name = f"Net-({uniq[0].component_ref}-Pad{uniq[0].pin_number})"
            else:
                name = f"Net-{anonymous_i}"

        is_bus = any(f.is_bus for f in frags) or is_bus_label(name)
        bus_members: list[str] = []
        for f in frags:
            for m in f.bus_members:
                if m not in bus_members:
                    bus_members.append(m)
        if is_bus and not bus_members:
            expanded = expand_bus_members(name)
            if expanded:
                bus_members = expanded

        bus_parent = next((f.bus_name for f in frags if f.bus_name), None)

        uuid_seed = f"{design_id}:{name}:" + ",".join(
            f"{e.component_ref}.{e.pin_number}" for e in uniq
        )
        constraints: list[Constraint] = []
        if bus_members:
            constraints.append(
                Constraint(name="bus_members", operator="in", value=list(bus_members))
            )
        if bus_parent:
            constraints.append(
                Constraint(name="bus", operator="eq", value=bus_parent)
            )
        nets.append(
            Net(
                name=name,
                endpoints=uniq,
                net_class=_infer_net_class(name, labels, is_bus=is_bus),
                voltage_domain=_infer_voltage_domain(name),
                uuid=str(uuid5(_NET_NS, uuid_seed)),
                constraints=constraints,
            )
        )

    nets.sort(key=lambda n: n.name)
    return nets


def _build_nets(graph: ConnectivityGraph, *, design_id: str) -> list[Net]:
    """Build nets from a single-sheet connectivity graph (test/helper path)."""
    fragments: list[_SheetNetFragment] = []
    for group in graph.net_groups():
        pins: list[PinAttachment] = group["pins"]
        labels: list[LabelAttachment] = group["labels"]
        if not pins and not labels:
            continue
        endpoints = [
            Endpoint(
                component_ref=p.component_ref,
                pin_number=p.pin_number,
                pin_name=p.pin_name,
            )
            for p in sorted(pins, key=lambda p: (p.component_ref, p.pin_number))
        ]
        fragments.append(
            _SheetNetFragment(
                sheet_path="/",
                endpoints=endpoints,
                labels=list(labels),
                name_hint=_choose_net_name(labels, pins),
            )
        )
    return _merge_hierarchy_nets(fragments, bridges=[], design_id=design_id)


def _choose_net_name(labels: list[LabelAttachment], pins: list[PinAttachment]) -> str | None:
    if not labels:
        return None
    # Prefer global, then hierarchical, then local; stable tie-break by name.
    priority = {"global": 0, "hierarchical": 1, "local": 2}
    labels_sorted = sorted(labels, key=lambda lb: (priority.get(lb.scope, 9), lb.name))
    return labels_sorted[0].name


def _infer_net_class(
    name: str,
    labels: list[LabelAttachment],
    *,
    is_bus: bool = False,
) -> NetClass:
    if is_bus or is_bus_label(name):
        return NetClass.BUS
    upper = name.upper()
    if upper in {"GND", "AGND", "DGND", "VSS", "PGND"} or upper.startswith("GND"):
        return NetClass.GROUND
    if any(upper.startswith(p) for p in ("+", "V", "VBAT", "VIN", "VCC", "VDD", "3V", "5V", "1V")):
        return NetClass.POWER
    if any(lb.scope == "global" for lb in labels) and upper in {"VIN", "VOUT", "3V3", "5V", "+3V3", "+5V"}:
        return NetClass.POWER
    return NetClass.SIGNAL


def _infer_voltage_domain(name: str) -> str | None:
    upper = name.upper().lstrip("+")
    if upper in {"GND", "AGND", "DGND", "VSS"}:
        return "GND"
    if upper in {"3V3", "3.3V", "VDD", "VCC"}:
        return "3V3"
    if upper in {"5V", "5.0V"}:
        return "5V"
    if upper == "VIN":
        return "3V3"
    return None


def _index_lib_symbol_pins(
    lib_symbols: SExprNode | None,
) -> dict[str, list[dict]]:
    """Map lib_id -> list of pin dicts {number, name, electrical, x, y, angle}."""
    index: dict[str, list[dict]] = {}
    if lib_symbols is None:
        return index
    for sym in lib_symbols.find_all("symbol"):
        lib_id = sym.atom_at(0)
        if not lib_id:
            continue
        pins: list[dict] = []
        for nested in sym.find_all("symbol"):
            for pin_node in nested.find_all("pin"):
                parsed = _parse_lib_pin(pin_node)
                if parsed is not None:
                    pins.append(parsed)
        # Also allow pins directly under the symbol (rare).
        for pin_node in sym.find_all("pin"):
            if pin_node.find("number") is None and pin_node.find("name") is None:
                continue
            parsed = _parse_lib_pin(pin_node)
            if parsed is not None:
                pins.append(parsed)
        # Deduplicate by pin number (unit variants may repeat).
        by_num: dict[str, dict] = {}
        for p in pins:
            by_num[p["number"]] = p
        index[lib_id] = list(by_num.values())
    return index


def _parse_lib_pin(pin_node: SExprNode) -> dict | None:
    # (pin passive line (at x y angle) (length ...) (name "...") (number "1") ...)
    if not pin_node.children:
        return None
    elec_atom = pin_node.children[0]
    elec = elec_atom.atom if isinstance(elec_atom, SExprNode) and elec_atom.is_atom else "unspecified"
    at = pin_node.find("at")
    number_node = pin_node.find("number")
    name_node = pin_node.find("name")
    if number_node is None:
        return None
    number = number_node.atom_at(0) or ""
    name = (name_node.atom_at(0) if name_node else None) or number
    x = y = angle = 0.0
    if at is not None:
        try:
            x = float(at.atom_at(0) or 0)
            y = float(at.atom_at(1) or 0)
            angle = float(at.atom_at(2) or 0)
        except ValueError:
            pass
    return {
        "number": number,
        "name": name if name != "~" else number,
        "electrical": elec or "unspecified",
        "x": x,
        "y": y,
        "angle": angle,
    }


def _symbol_instance_to_component(
    sym: SExprNode,
    lib_pins: dict[str, list[dict]],
    *,
    sheet_path: str = "/",
    file_path: str | None = None,
) -> tuple[Component | None, list[PinAttachment]]:
    lib_id_node = sym.find("lib_id")
    if lib_id_node is None:
        return None, []
    lib_id = lib_id_node.atom_at(0) or ""
    props = _properties(sym)
    property_reference = props.get("Reference") or props.get("reference")
    # Hierarchy walk path is authoritative; instances block supplies per-instance ref.
    reference = symbol_instance_reference(
        sym, sheet_path=sheet_path, fallback=property_reference
    )
    if not reference:
        return None, []

    at = sym.find("at")
    ix = iy = iangle = 0.0
    if at is not None:
        try:
            ix = float(at.atom_at(0) or 0)
            iy = float(at.atom_at(1) or 0)
            iangle = float(at.atom_at(2) or 0)
        except ValueError:
            pass

    mirror_x = any(c.head == "mirror" and c.atom_at(0) == "x" for c in sym.children if isinstance(c, SExprNode))
    mirror_y = any(c.head == "mirror" and c.atom_at(0) == "y" for c in sym.children if isinstance(c, SExprNode))

    uuid = _first_atom(sym.find("uuid")) or str(
        uuid5(_NET_NS, f"comp:{reference}:{lib_id}:{ix}:{iy}:{sheet_path}")
    )
    value = props.get("Value")
    footprint = props.get("Footprint") or None
    if footprint == "":
        footprint = None

    is_power = bool(sym.find("dnp") is None and (reference.startswith("#PWR") or lib_id.startswith("power:")))
    # lib_symbols mark power symbols with (power); instances inherit via lib_id prefix.
    if lib_id.startswith("power:"):
        is_power = True

    pin_defs = lib_pins.get(lib_id, [])
    # Fall back to instance pin numbers if library missing.
    if not pin_defs:
        pin_defs = [
            {
                "number": (p.atom_at(0) or ""),
                "name": p.atom_at(0) or "",
                "electrical": "unspecified",
                "x": 0.0,
                "y": 0.0,
                "angle": 0.0,
            }
            for p in sym.find_all("pin")
            if p.atom_at(0)
        ]

    pins: list[Pin] = []
    attachments: list[PinAttachment] = []
    for pdef in sorted(pin_defs, key=lambda p: p["number"]):
        role = _PIN_TYPE_MAP.get(str(pdef["electrical"]), ElectricalRole.UNSPECIFIED)
        pins.append(
            Pin(
                number=str(pdef["number"]),
                name=str(pdef["name"]),
                electrical_role=role,
            )
        )
        wx, wy = _transform_point(
            float(pdef["x"]),
            float(pdef["y"]),
            ix,
            iy,
            iangle,
            mirror_x=mirror_x,
            mirror_y=mirror_y,
        )
        attachments.append(
            PinAttachment(
                component_ref=reference,
                pin_number=str(pdef["number"]),
                pin_name=str(pdef["name"]),
                point=qpoint(wx, wy),
                uuid=uuid,
            )
        )

    attributes: dict = {"lib_id": lib_id, "sheet_path": sheet_path}
    if is_power:
        attributes["power_symbol"] = True
    mpn = props.get("MPN") or props.get("Manufacturer_Part_Number")

    component = Component(
        reference=reference,
        manufacturer_part_number=mpn,
        value=value,
        functional_class=_infer_functional_class(reference, lib_id),
        symbol_ref=lib_id,
        footprint_ref=footprint,
        pins=pins,
        attributes=attributes,
        source_location=SourceLocation(
            uuid=uuid,
            x=ix,
            y=iy,
            sheet=sheet_path,
            path=file_path,
        ),
        uuid=uuid,
    )
    return component, attachments


def _transform_point(
    lx: float,
    ly: float,
    ix: float,
    iy: float,
    angle_deg: float,
    *,
    mirror_x: bool = False,
    mirror_y: bool = False,
) -> tuple[float, float]:
    x, y = lx, ly
    if mirror_x:
        x = -x
    if mirror_y:
        y = -y
    rad = math.radians(angle_deg % 360.0)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = x * cos_a - y * sin_a
    ry = x * sin_a + y * cos_a
    return ix + rx, iy + ry


def _properties(sym: SExprNode) -> dict[str, str]:
    props: dict[str, str] = {}
    for prop in sym.find_all("property"):
        key = prop.atom_at(0)
        val = prop.atom_at(1)
        if key is not None and val is not None:
            props[key] = val
    return props


def _infer_functional_class(reference: str, lib_id: str) -> FunctionalClass:
    lower = lib_id.lower()
    if "regulator" in lower or "ldo" in lower:
        return FunctionalClass.REGULATOR_LDO
    if "connector" in lower:
        return FunctionalClass.CONNECTOR
    if lower.startswith("device:r") or lower.startswith("device:c") or lower.startswith("device:l"):
        return FunctionalClass.PASSIVE
    for pattern, cls in _REF_CLASS:
        if pattern.match(reference):
            return cls
    return FunctionalClass.OTHER


def _fragments_from_graph(
    graph: ConnectivityGraph,
    *,
    sheet_path: str,
    is_bus: bool,
) -> list[_SheetNetFragment]:
    fragments: list[_SheetNetFragment] = []
    for group in graph.net_groups():
        pins: list[PinAttachment] = group["pins"]
        labels: list[LabelAttachment] = group["labels"]
        if not pins and not labels:
            continue
        endpoints = [
            Endpoint(
                component_ref=p.component_ref,
                pin_number=p.pin_number,
                pin_name=p.pin_name,
            )
            for p in sorted(pins, key=lambda p: (p.component_ref, p.pin_number))
        ]
        seen: set[tuple[str, str]] = set()
        uniq: list[Endpoint] = []
        for ep in endpoints:
            key = (ep.component_ref, ep.pin_number)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(ep)
        name_hint = _choose_net_name(labels, pins)
        members: list[str] = []
        if is_bus and name_hint:
            expanded = expand_bus_members(name_hint)
            if expanded:
                members = expanded
        elif is_bus:
            for lb in labels:
                expanded = expand_bus_members(lb.name)
                if expanded:
                    members = expanded
                    if name_hint is None:
                        name_hint = lb.name
                    break
        fragments.append(
            _SheetNetFragment(
                sheet_path=sheet_path,
                endpoints=uniq,
                labels=list(labels),
                name_hint=name_hint,
                is_bus=is_bus or bool(members),
                bus_members=members,
            )
        )
    return fragments


def _annotate_bus_entry_membership(
    fragments: list[_SheetNetFragment],
    bus_entries: list[tuple[Point, Point]],
    wire_graph: ConnectivityGraph,
    bus_graph: ConnectivityGraph,
) -> None:
    """Mark wire nets that attach to a bus when their name matches a bus member."""
    if not bus_entries:
        return

    wire_by_root: dict[Point, _SheetNetFragment] = {}
    bus_by_root: dict[Point, _SheetNetFragment] = {}
    for frag in fragments:
        graph = bus_graph if frag.is_bus else wire_graph
        index = bus_by_root if frag.is_bus else wire_by_root
        for lb in frag.labels:
            if graph.uf.has(lb.point):
                index[graph.uf.find(lb.point)] = frag
        for pin in graph.pins:
            if any(
                ep.component_ref == pin.component_ref and ep.pin_number == pin.pin_number
                for ep in frag.endpoints
            ):
                if graph.uf.has(pin.point):
                    index[graph.uf.find(pin.point)] = frag

    for a, b in bus_entries:
        for wire_pt, bus_pt in ((a, b), (b, a)):
            if not wire_graph.uf.has(wire_pt) or not bus_graph.uf.has(bus_pt):
                continue
            wfrag = wire_by_root.get(wire_graph.uf.find(wire_pt))
            bfrag = bus_by_root.get(bus_graph.uf.find(bus_pt))
            if wfrag is None or bfrag is None:
                continue
            bus_name = bfrag.name_hint
            members = list(bfrag.bus_members)
            if bus_name and not members:
                members = expand_bus_members(bus_name) or []
            if not bus_name or not members:
                continue
            wire_name = wfrag.name_hint
            if wire_name and wire_name in members:
                wfrag.bus_name = bus_name


def _qualify_reused_symbol_uuids(components: list[Component]) -> None:
    """When the same CAD uuid is instantiated on multiple sheets, qualify IR uuids."""
    by_uuid: dict[str, list[Component]] = {}
    for comp in components:
        by_uuid.setdefault(comp.uuid, []).append(comp)
    for cad_uuid, group in by_uuid.items():
        sheets = {
            (c.source_location.sheet if c.source_location else None) for c in group
        }
        if len(group) < 2 or len(sheets) < 2:
            continue
        for comp in group:
            sheet = comp.source_location.sheet if comp.source_location else "/"
            new_uuid = str(uuid5(_NET_NS, f"instance:{sheet}:{cad_uuid}"))
            if comp.source_location is not None:
                comp.source_location.uuid = cad_uuid
            comp.attributes = {**comp.attributes, "cad_uuid": cad_uuid}
            comp.uuid = new_uuid


def _bus_entry_points(entry: SExprNode) -> tuple[Point, Point] | None:
    """Return (at, at+size) endpoints for a bus_entry."""
    at = entry.find("at")
    size = entry.find("size")
    if at is None or size is None:
        return None
    try:
        x = float(at.atom_at(0) or 0)
        y = float(at.atom_at(1) or 0)
        dx = float(size.atom_at(0) or 0)
        dy = float(size.atom_at(1) or 0)
    except ValueError:
        return None
    return qpoint(x, y), qpoint(x + dx, y + dy)


def _wire_points(wire: SExprNode) -> list[Point]:
    pts_node = wire.find("pts")
    if pts_node is None:
        return []
    points: list[Point] = []
    for xy in pts_node.find_all("xy"):
        try:
            x = float(xy.atom_at(0) or 0)
            y = float(xy.atom_at(1) or 0)
        except ValueError:
            continue
        points.append(qpoint(x, y))
    return points


def _polyline_points(poly: SExprNode) -> list[Point]:
    return _wire_points(poly)


def _at_point(at: SExprNode) -> Point | None:
    try:
        x = float(at.atom_at(0) or 0)
        y = float(at.atom_at(1) or 0)
    except ValueError:
        return None
    return qpoint(x, y)


def _first_atom(node: SExprNode | None) -> str | None:
    if node is None:
        return None
    return node.atom_at(0)


def _title_block_name(root: SExprNode) -> str | None:
    title_block = root.find("title_block")
    if title_block is None:
        return None
    title = title_block.find("title")
    return _first_atom(title)
