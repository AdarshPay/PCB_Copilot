"""Emit a minimal KiCad schematic S-expression from Circuit IR.

Produces a simplified but connectivity-faithful `.kicad_sch` suitable for
semantic round-trip tests (normalize → emit → normalize). Geometry is synthetic
and not intended for interactive editing in KiCad.
"""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design, ElectricalRole, NetClass
from pcb_ai_kicad_adapter.parser import SExprNode, dump_schematic_sexpr

_ROLE_TO_KICAD = {
    ElectricalRole.POWER_IN: "power_in",
    ElectricalRole.POWER_OUT: "power_out",
    ElectricalRole.GROUND: "power_in",
    ElectricalRole.DIGITAL_IN: "input",
    ElectricalRole.DIGITAL_OUT: "output",
    ElectricalRole.DIGITAL_BIDIR: "bidirectional",
    ElectricalRole.OPEN_DRAIN: "open_collector",
    ElectricalRole.ANALOG_IN: "input",
    ElectricalRole.ANALOG_OUT: "output",
    ElectricalRole.CLOCK: "input",
    ElectricalRole.RESET: "input",
    ElectricalRole.BOOT: "input",
    ElectricalRole.ENABLE: "input",
    ElectricalRole.NO_CONNECT: "no_connect",
    ElectricalRole.PASSIVE: "passive",
    ElectricalRole.UNSPECIFIED: "unspecified",
}


def emit_schematic_ast(design: Design) -> SExprNode:
    """Build a `kicad_sch` AST that preserves component/pin/net semantics."""
    # Layout: place components on a grid; draw wires for nets between pin points.
    lib_symbols = _build_lib_symbols(design)
    children: list[SExprNode] = [
        SExprNode(head="version", children=[SExprNode(atom=design.source_version or "20250114")]),
        SExprNode(head="generator", children=[SExprNode(atom="pcb-ai")]),
        SExprNode(head="uuid", children=[SExprNode(atom=design.id)]),
        SExprNode(head="paper", children=[SExprNode(atom="A4")]),
        SExprNode(
            head="title_block",
            children=[SExprNode(head="title", children=[SExprNode(atom=design.name or design.id)])],
        ),
        lib_symbols,
    ]

    # Assign positions: each component gets a column.
    pin_points: dict[tuple[str, str], tuple[float, float]] = {}
    spacing_x = 40.0
    for idx, component in enumerate(design.components):
        origin_x = 50.0 + idx * spacing_x
        origin_y = 80.0
        lib_id = component.symbol_ref or f"Synthetic:{component.reference}"
        pin_nodes: list[SExprNode] = []
        for p_i, pin in enumerate(component.pins):
            # Match emit library pin local coords: pin i at (0, 5 - i*5) roughly
            local_y = 5.0 - p_i * 5.0
            wx, wy = origin_x, origin_y + local_y
            pin_points[(component.reference, pin.number)] = (wx, wy)
            pin_nodes.append(
                SExprNode(
                    head="pin",
                    children=[
                        SExprNode(atom=pin.number),
                        SExprNode(head="uuid", children=[SExprNode(atom=f"{component.uuid}-p{pin.number}")]),
                    ],
                )
            )

        sym_children: list[SExprNode] = [
            SExprNode(head="lib_id", children=[SExprNode(atom=lib_id)]),
            SExprNode(
                head="at",
                children=[
                    SExprNode(atom=str(origin_x)),
                    SExprNode(atom=str(origin_y)),
                    SExprNode(atom="0"),
                ],
            ),
            SExprNode(head="unit", children=[SExprNode(atom="1")]),
            SExprNode(head="uuid", children=[SExprNode(atom=component.uuid)]),
            _property("Reference", component.reference),
            _property("Value", component.value or component.reference),
            _property("Footprint", component.footprint_ref or ""),
            *pin_nodes,
        ]
        children.append(SExprNode(head="symbol", children=sym_children))

    # For each net: place a label at the first endpoint and wire all endpoints together.
    for n_i, net in enumerate(design.nets):
        if not net.endpoints:
            continue
        pts: list[tuple[float, float]] = []
        for ep in net.endpoints:
            key = (ep.component_ref, ep.pin_number)
            if key in pin_points:
                pts.append(pin_points[key])
        if not pts:
            continue
        # Star-connect via a junction slightly offset.
        hub = (pts[0][0] + 10.0 + n_i, pts[0][1])
        for pt in pts:
            children.append(_wire(pt, hub, uuid=f"{net.uuid}-w-{pt[0]}-{pt[1]}"))
        children.append(
            SExprNode(
                head="junction",
                children=[
                    SExprNode(
                        head="at",
                        children=[SExprNode(atom=str(hub[0])), SExprNode(atom=str(hub[1]))],
                    ),
                    SExprNode(head="uuid", children=[SExprNode(atom=f"{net.uuid}-j")]),
                ],
            )
        )
        label_head = "global_label" if net.net_class in {NetClass.POWER, NetClass.GROUND} else "label"
        children.append(
            SExprNode(
                head=label_head,
                children=[
                    SExprNode(atom=net.name),
                    SExprNode(
                        head="at",
                        children=[
                            SExprNode(atom=str(hub[0])),
                            SExprNode(atom=str(hub[1])),
                            SExprNode(atom="0"),
                        ],
                    ),
                    SExprNode(head="uuid", children=[SExprNode(atom=net.uuid)]),
                ],
            )
        )

    return SExprNode(head="kicad_sch", children=children)


def emit_schematic_text(design: Design) -> str:
    return dump_schematic_sexpr(emit_schematic_ast(design))


def _build_lib_symbols(design: Design) -> SExprNode:
    seen: set[str] = set()
    symbols: list[SExprNode] = []
    for component in design.components:
        lib_id = component.symbol_ref or f"Synthetic:{component.reference}"
        if lib_id in seen:
            continue
        seen.add(lib_id)
        unit_pins: list[SExprNode] = []
        for p_i, pin in enumerate(component.pins):
            local_y = 5.0 - p_i * 5.0
            ktype = _ROLE_TO_KICAD.get(pin.electrical_role, "unspecified")
            unit_pins.append(
                SExprNode(
                    head="pin",
                    children=[
                        SExprNode(atom=ktype),
                        SExprNode(atom="line"),
                        SExprNode(
                            head="at",
                            children=[
                                SExprNode(atom="0"),
                                SExprNode(atom=str(local_y)),
                                SExprNode(atom="0"),
                            ],
                        ),
                        SExprNode(head="length", children=[SExprNode(atom="2.54")]),
                        SExprNode(head="name", children=[SExprNode(atom=pin.name)]),
                        SExprNode(head="number", children=[SExprNode(atom=pin.number)]),
                    ],
                )
            )
        short = lib_id.split(":")[-1]
        symbols.append(
            SExprNode(
                head="symbol",
                children=[
                    SExprNode(atom=lib_id),
                    _property("Reference", component.reference[0] if component.reference else "U"),
                    _property("Value", short),
                    _property("Footprint", ""),
                    SExprNode(
                        head="symbol",
                        children=[SExprNode(atom=f"{short}_1_1"), *unit_pins],
                    ),
                ],
            )
        )
    return SExprNode(head="lib_symbols", children=symbols)


def _property(key: str, value: str) -> SExprNode:
    return SExprNode(
        head="property",
        children=[
            SExprNode(atom=key),
            SExprNode(atom=value),
            SExprNode(
                head="at",
                children=[SExprNode(atom="0"), SExprNode(atom="0"), SExprNode(atom="0")],
            ),
            SExprNode(
                head="effects",
                children=[SExprNode(head="font", children=[SExprNode(head="size", children=[SExprNode(atom="1.27"), SExprNode(atom="1.27")])])],
            ),
        ],
    )


def _wire(a: tuple[float, float], b: tuple[float, float], *, uuid: str) -> SExprNode:
    return SExprNode(
        head="wire",
        children=[
            SExprNode(
                head="pts",
                children=[
                    SExprNode(
                        head="xy",
                        children=[SExprNode(atom=str(a[0])), SExprNode(atom=str(a[1]))],
                    ),
                    SExprNode(
                        head="xy",
                        children=[SExprNode(atom=str(b[0])), SExprNode(atom=str(b[1]))],
                    ),
                ],
            ),
            SExprNode(
                head="stroke",
                children=[
                    SExprNode(head="width", children=[SExprNode(atom="0")]),
                    SExprNode(head="type", children=[SExprNode(atom="default")]),
                ],
            ),
            SExprNode(head="uuid", children=[SExprNode(atom=uuid)]),
        ],
    )
