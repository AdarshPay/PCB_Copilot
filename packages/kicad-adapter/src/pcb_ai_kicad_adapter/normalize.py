"""Normalize KiCad schematic AST into Circuit IR."""

from __future__ import annotations

import math
import re
from pathlib import Path
from uuid import uuid5, UUID

from pcb_ai_circuit_ir.models import (
    Component,
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
from pcb_ai_kicad_adapter.parser import SExprNode, parse_schematic_sexpr

# Stable namespace for deterministic net UUIDs derived from schematic content.
_NET_NS = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


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


def normalize_to_circuit_ir(ast: SExprNode | Design, *, design_id: str | None = None) -> Design:
    """Convert a parsed schematic AST into a typed Design.

    If a Design is passed through (e.g. golden fixtures), it is returned as-is.
    """
    if isinstance(ast, Design):
        return ast
    if ast.head != "kicad_sch":
        raise NormalizationError(f"Expected kicad_sch root, got {ast.head!r}")
    return _normalize_schematic(ast, design_id=design_id)


def ingest_schematic(
    source: str | Path,
    *,
    design_id: str | None = None,
) -> Design:
    """Parse a `.kicad_sch` path or text and normalize to Circuit IR."""
    path: Path | None = None
    if isinstance(source, Path):
        path = source
        ast = parse_schematic_sexpr(source)
        default_id = design_id or f"kicad.{source.stem}"
    elif isinstance(source, str) and "\n" not in source and source.endswith(".kicad_sch"):
        path = Path(source)
        if path.is_file():
            ast = parse_schematic_sexpr(path)
            default_id = design_id or f"kicad.{path.stem}"
        else:
            ast = parse_schematic_sexpr(source)
            default_id = design_id or "kicad.inline"
    else:
        ast = parse_schematic_sexpr(source)
        default_id = design_id or "kicad.inline"
    design = normalize_to_circuit_ir(ast, design_id=default_id)
    if path is not None:
        for component in design.components:
            if component.source_location is None:
                component.source_location = SourceLocation(path=str(path))
            elif component.source_location.path is None:
                component.source_location.path = str(path)
    return design


def _normalize_schematic(root: SExprNode, *, design_id: str | None) -> Design:
    version = _first_atom(root.find("version"))
    sheet_uuid = _first_atom(root.find("uuid"))
    title = _title_block_name(root)

    lib_pins = _index_lib_symbol_pins(root.find("lib_symbols"))
    components: list[Component] = []
    graph = ConnectivityGraph()
    instance_pin_points: list[tuple[Component, list[PinAttachment]]] = []

    for sym in root.find_all("symbol"):
        # Skip nested library definitions accidentally present under root.
        if sym.find("lib_id") is None and sym.find("pin") is None:
            continue
        component, attachments = _symbol_instance_to_component(sym, lib_pins)
        if component is None:
            continue
        components.append(component)
        instance_pin_points.append((component, attachments))
        for att in attachments:
            graph.add_pin(att)

    for wire in root.find_all("wire"):
        pts = _wire_points(wire)
        uuid = _first_atom(wire.find("uuid"))
        for i in range(len(pts) - 1):
            graph.add_wire(pts[i], pts[i + 1], uuid=uuid)

    for poly in root.find_all("polyline"):
        # Some exports use polyline for bus-like geometry; treat as wires.
        pts = _polyline_points(poly)
        uuid = _first_atom(poly.find("uuid"))
        for i in range(len(pts) - 1):
            graph.add_wire(pts[i], pts[i + 1], uuid=uuid)

    for jn in root.find_all("junction"):
        at = jn.find("at")
        if at is not None:
            pt = _at_point(at)
            if pt is not None:
                graph.add_junction(pt)

    for label in root.find_all("label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                graph.add_label(
                    LabelAttachment(
                        name=name,
                        point=pt,
                        scope="local",
                        uuid=_first_atom(label.find("uuid")),
                    )
                )

    for label in root.find_all("global_label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                graph.add_label(
                    LabelAttachment(
                        name=name,
                        point=pt,
                        scope="global",
                        uuid=_first_atom(label.find("uuid")),
                    )
                )

    for label in root.find_all("hierarchical_label"):
        name = label.atom_at(0)
        at = label.find("at")
        if name and at is not None:
            pt = _at_point(at)
            if pt is not None:
                graph.add_label(
                    LabelAttachment(
                        name=name,
                        point=pt,
                        scope="hierarchical",
                        uuid=_first_atom(label.find("uuid")),
                    )
                )

    # Power-symbol net naming: Value property is the global net name.
    for component, attachments in instance_pin_points:
        if component.reference.startswith("#PWR") or component.attributes.get("power_symbol"):
            net_name = component.value or component.reference
            for att in attachments:
                graph.add_label(
                    LabelAttachment(
                        name=net_name,
                        point=att.point,
                        scope="global",
                        uuid=component.uuid,
                    )
                )

    nets = _build_nets(graph, design_id=design_id or sheet_uuid or "kicad")

    return Design(
        id=design_id or (f"kicad.{sheet_uuid}" if sheet_uuid else "kicad.unknown"),
        source_tool=SourceTool.KICAD,
        source_version=version,
        revision="0",
        name=title,
        components=components,
        nets=nets,
    )


def _build_nets(graph: ConnectivityGraph, *, design_id: str) -> list[Net]:
    nets: list[Net] = []
    anonymous_i = 0
    for group in graph.net_groups():
        pins: list[PinAttachment] = group["pins"]
        labels: list[LabelAttachment] = group["labels"]
        if not pins and not labels:
            continue

        name = _choose_net_name(labels, pins)
        if name is None:
            anonymous_i += 1
            if pins:
                p0 = pins[0]
                name = f"Net-({p0.component_ref}-Pad{p0.pin_number})"
            else:
                name = f"Net-{anonymous_i}"

        endpoints = [
            Endpoint(
                component_ref=p.component_ref,
                pin_number=p.pin_number,
                pin_name=p.pin_name,
            )
            for p in sorted(pins, key=lambda p: (p.component_ref, p.pin_number))
        ]
        # Deduplicate endpoints
        seen: set[tuple[str, str]] = set()
        uniq: list[Endpoint] = []
        for ep in endpoints:
            key = (ep.component_ref, ep.pin_number)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(ep)

        net_class = _infer_net_class(name, labels)
        uuid_seed = f"{design_id}:{name}:" + ",".join(f"{e.component_ref}.{e.pin_number}" for e in uniq)
        nets.append(
            Net(
                name=name,
                endpoints=uniq,
                net_class=net_class,
                voltage_domain=_infer_voltage_domain(name),
                uuid=str(uuid5(_NET_NS, uuid_seed)),
            )
        )

    nets.sort(key=lambda n: n.name)
    return nets


def _choose_net_name(labels: list[LabelAttachment], pins: list[PinAttachment]) -> str | None:
    if not labels:
        return None
    # Prefer global, then hierarchical, then local; stable tie-break by name.
    priority = {"global": 0, "hierarchical": 1, "local": 2}
    labels_sorted = sorted(labels, key=lambda lb: (priority.get(lb.scope, 9), lb.name))
    return labels_sorted[0].name


def _infer_net_class(name: str, labels: list[LabelAttachment]) -> NetClass:
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
) -> tuple[Component | None, list[PinAttachment]]:
    lib_id_node = sym.find("lib_id")
    if lib_id_node is None:
        return None, []
    lib_id = lib_id_node.atom_at(0) or ""
    props = _properties(sym)
    reference = props.get("Reference") or props.get("reference")
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

    uuid = _first_atom(sym.find("uuid")) or str(uuid5(_NET_NS, f"comp:{reference}:{lib_id}:{ix}:{iy}"))
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

    attributes: dict = {"lib_id": lib_id}
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
        source_location=SourceLocation(uuid=uuid, x=ix, y=iy, sheet="/"),
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
