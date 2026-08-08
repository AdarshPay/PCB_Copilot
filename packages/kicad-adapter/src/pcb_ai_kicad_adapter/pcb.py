"""KiCad `.kicad_pcb` ingest / emit for Phase B MVP subset.

Supported subset (KiCad 10 style): footprints with pads, nets, segments,
vias, rectangular Edge.Cuts outline. Geometry is connectivity-faithful on
emit — not a lossless rewrite of arbitrary hand-laid boards.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pcb_ai_pcb_ir.models import (
    Board,
    BoardNet,
    FootprintInstance,
    Layer,
    Outline,
    Pad,
    Placement,
    Point,
    Track,
    Via,
)
from pcb_ai_kicad_adapter.parser import SExprNode, parse_schematic_sexpr, serialize_sexpr


def parse_pcb_sexpr(text: str) -> SExprNode:
    """Parse a ``kicad_pcb`` document (same S-expr grammar as schematics)."""
    root = parse_schematic_sexpr(text)
    if root.head not in {"kicad_pcb", "kicad_sch"}:
        # Allow either; PCB files use kicad_pcb.
        pass
    return root


def ingest_pcb(path: str | Path) -> Board:
    """Load a ``.kicad_pcb`` file into Board IR (MVP subset)."""
    pcb_path = Path(path)
    text = pcb_path.read_text(encoding="utf-8")
    root = parse_pcb_sexpr(text)
    return normalize_pcb_to_board(root, board_id=f"pcb:{pcb_path.stem}")


def normalize_pcb_to_board(root: SExprNode, *, board_id: str = "pcb") -> Board:
    """Convert a ``kicad_pcb`` AST into Board IR."""
    nets: list[BoardNet] = []
    net_by_code: dict[str, str] = {}
    for net_node in root.find_all("net"):
        code = net_node.atom_at(0) or "0"
        name = net_node.atom_at(1) or f"Net-{code}"
        # Strip quotes if present from tokenizer
        name = name.strip('"')
        net_by_code[code] = name
        if name and name != "":
            nets.append(BoardNet(name=name))

    footprints: list[FootprintInstance] = []
    for fp in root.find_all("footprint"):
        footprints.append(_parse_footprint(fp, net_by_code))

    tracks: list[Track] = []
    for seg in root.find_all("segment"):
        track = _parse_segment(seg, net_by_code)
        if track is not None:
            tracks.append(track)

    vias: list[Via] = []
    for via_node in root.find_all("via"):
        via = _parse_via(via_node, net_by_code)
        if via is not None:
            vias.append(via)

    outline = _parse_outline(root)

    return Board(
        id=board_id,
        name=board_id,
        outline=outline,
        footprints=footprints,
        nets=nets,
        tracks=tracks,
        vias=vias,
    )


def _parse_footprint(fp: SExprNode, net_by_code: dict[str, str]) -> FootprintInstance:
    footprint_ref = (fp.atom_at(0) or "Unknown").strip('"')
    at = fp.find("at")
    x = float(at.atom_at(0) or 0) if at else 0.0
    y = float(at.atom_at(1) or 0) if at else 0.0
    rot = float(at.atom_at(2) or 0) if at and at.atom_at(2) else 0.0
    layer_node = fp.find("layer")
    layer_name = (layer_node.atom_at(0) if layer_node else "F.Cu") or "F.Cu"
    layer_name = layer_name.strip('"')
    try:
        layer = Layer(layer_name)
    except ValueError:
        layer = Layer.F_CU

    ref = footprint_ref
    value = None
    for prop in fp.find_all("property"):
        key = (prop.atom_at(0) or "").strip('"')
        val = (prop.atom_at(1) or "").strip('"')
        if key == "Reference":
            ref = val
        elif key == "Value":
            value = val
    # KiCad also uses (fp_text reference ...)
    for text in fp.find_all("fp_text"):
        kind = (text.atom_at(0) or "").strip('"')
        val = (text.atom_at(1) or "").strip('"')
        if kind == "reference":
            ref = val
        elif kind == "value":
            value = val

    pads: list[Pad] = []
    for pad_node in fp.find_all("pad"):
        pads.append(_parse_pad(pad_node, net_by_code))

    placed = at is not None
    return FootprintInstance(
        reference=ref,
        footprint_ref=footprint_ref,
        value=value,
        placement=Placement(x=x, y=y, rotation_deg=rot, layer=layer, placed=placed),
        pads=pads,
        uuid=str(uuid4()),
    )


def _parse_pad(pad_node: SExprNode, net_by_code: dict[str, str]) -> Pad:
    number = (pad_node.atom_at(0) or "1").strip('"')
    at = pad_node.find("at")
    x = float(at.atom_at(0) or 0) if at else 0.0
    y = float(at.atom_at(1) or 0) if at else 0.0
    size = pad_node.find("size")
    w = float(size.atom_at(0) or 1) if size else 1.0
    h = float(size.atom_at(1) or 1) if size else 1.0
    net_name = None
    net = pad_node.find("net")
    if net is not None:
        code = net.atom_at(0) or ""
        name = (net.atom_at(1) or net_by_code.get(code, "")).strip('"')
        net_name = name or net_by_code.get(code)
    return Pad(number=number, net_name=net_name, x=x, y=y, width=w, height=h)


def _parse_segment(seg: SExprNode, net_by_code: dict[str, str]) -> Track | None:
    start = seg.find("start")
    end = seg.find("end")
    if start is None or end is None:
        return None
    width_node = seg.find("width")
    layer_node = seg.find("layer")
    net = seg.find("net")
    net_name = ""
    if net is not None:
        code = net.atom_at(0) or ""
        net_name = (net.atom_at(1) or net_by_code.get(code, f"Net-{code}")).strip('"')
    layer_name = ((layer_node.atom_at(0) if layer_node else "F.Cu") or "F.Cu").strip('"')
    try:
        layer = Layer(layer_name)
    except ValueError:
        layer = Layer.F_CU
    return Track(
        net_name=net_name,
        layer=layer,
        start=Point(x=float(start.atom_at(0) or 0), y=float(start.atom_at(1) or 0)),
        end=Point(x=float(end.atom_at(0) or 0), y=float(end.atom_at(1) or 0)),
        width=float(width_node.atom_at(0) or 0.25) if width_node else 0.25,
    )


def _parse_via(via_node: SExprNode, net_by_code: dict[str, str]) -> Via | None:
    at = via_node.find("at")
    if at is None:
        return None
    size_node = via_node.find("size")
    drill_node = via_node.find("drill")
    net = via_node.find("net")
    net_name = ""
    if net is not None:
        code = net.atom_at(0) or ""
        net_name = (net.atom_at(1) or net_by_code.get(code, "")).strip('"')
    return Via(
        net_name=net_name,
        at=Point(x=float(at.atom_at(0) or 0), y=float(at.atom_at(1) or 0)),
        size=float(size_node.atom_at(0) or 0.6) if size_node else 0.6,
        drill=float(drill_node.atom_at(0) or 0.3) if drill_node else 0.3,
    )


def _parse_outline(root: SExprNode) -> Outline:
    """Infer rectangular outline from Edge.Cuts gr_line / gr_rect if present."""
    xs: list[float] = []
    ys: list[float] = []
    for line in root.find_all("gr_line"):
        layer = line.find("layer")
        layer_name = ((layer.atom_at(0) if layer else "") or "").strip('"')
        if layer_name != "Edge.Cuts":
            continue
        for tag in ("start", "end"):
            pt = line.find(tag)
            if pt:
                xs.append(float(pt.atom_at(0) or 0))
                ys.append(float(pt.atom_at(1) or 0))
    for rect in root.find_all("gr_rect"):
        layer = rect.find("layer")
        layer_name = ((layer.atom_at(0) if layer else "") or "").strip('"')
        if layer_name != "Edge.Cuts":
            continue
        start = rect.find("start")
        end = rect.find("end")
        if start and end:
            xs.extend([float(start.atom_at(0) or 0), float(end.atom_at(0) or 0)])
            ys.extend([float(start.atom_at(1) or 0), float(end.atom_at(1) or 0)])
    if xs and ys:
        return Outline(
            width=max(xs) - min(xs),
            height=max(ys) - min(ys),
            origin=Point(x=min(xs), y=min(ys)),
        )
    return Outline()


def emit_pcb_ast(board: Board) -> SExprNode:
    """Build a KiCad 10-ish ``kicad_pcb`` AST from Board IR."""
    children: list[SExprNode] = [
        SExprNode(head="version", children=[SExprNode(atom="20240108")]),
        SExprNode(head="generator", children=[SExprNode(atom="pcb-ai")]),
        SExprNode(head="general", children=[
            SExprNode(head="thickness", children=[SExprNode(atom="1.6")]),
        ]),
        SExprNode(head="paper", children=[SExprNode(atom="A4")]),
        SExprNode(head="layers", children=[
            SExprNode(head="0", children=[SExprNode(atom="F.Cu"), SExprNode(atom="signal")]),
            SExprNode(head="31", children=[SExprNode(atom="B.Cu"), SExprNode(atom="signal")]),
            SExprNode(head="44", children=[SExprNode(atom="Edge.Cuts"), SExprNode(atom="user")]),
        ]),
    ]

    # Net 0 is empty / reserved.
    children.append(SExprNode(head="net", children=[SExprNode(atom="0"), SExprNode(atom="")]))
    net_codes: dict[str, int] = {"": 0}
    for i, net in enumerate(board.nets, start=1):
        net_codes[net.name] = i
        children.append(
            SExprNode(
                head="net",
                children=[
                    SExprNode(atom=str(i)),
                    SExprNode(atom=net.name),
                ],
            )
        )

    ox, oy = board.outline.origin.x, board.outline.origin.y
    w, h = board.outline.width, board.outline.height
    corners = [(ox, oy), (ox + w, oy), (ox + w, oy + h), (ox, oy + h)]
    for i, (x1, y1) in enumerate(corners):
        x2, y2 = corners[(i + 1) % 4]
        children.append(
            SExprNode(
                head="gr_line",
                children=[
                    SExprNode(head="start", children=[SExprNode(atom=str(x1)), SExprNode(atom=str(y1))]),
                    SExprNode(head="end", children=[SExprNode(atom=str(x2)), SExprNode(atom=str(y2))]),
                    SExprNode(head="stroke", children=[
                        SExprNode(head="width", children=[SExprNode(atom="0.1")]),
                        SExprNode(head="type", children=[SExprNode(atom="default")]),
                    ]),
                    SExprNode(head="layer", children=[SExprNode(atom="Edge.Cuts")]),
                ],
            )
        )

    for fp in board.footprints:
        children.append(_emit_footprint(fp, net_codes))

    for track in board.tracks:
        code = net_codes.get(track.net_name, 0)
        children.append(
            SExprNode(
                head="segment",
                children=[
                    SExprNode(
                        head="start",
                        children=[SExprNode(atom=str(track.start.x)), SExprNode(atom=str(track.start.y))],
                    ),
                    SExprNode(
                        head="end",
                        children=[SExprNode(atom=str(track.end.x)), SExprNode(atom=str(track.end.y))],
                    ),
                    SExprNode(head="width", children=[SExprNode(atom=str(track.width))]),
                    SExprNode(head="layer", children=[SExprNode(atom=track.layer.value)]),
                    SExprNode(head="net", children=[SExprNode(atom=str(code))]),
                ],
            )
        )

    for via in board.vias:
        code = net_codes.get(via.net_name, 0)
        children.append(
            SExprNode(
                head="via",
                children=[
                    SExprNode(
                        head="at",
                        children=[SExprNode(atom=str(via.at.x)), SExprNode(atom=str(via.at.y))],
                    ),
                    SExprNode(head="size", children=[SExprNode(atom=str(via.size))]),
                    SExprNode(head="drill", children=[SExprNode(atom=str(via.drill))]),
                    SExprNode(
                        head="layers",
                        children=[SExprNode(atom="F.Cu"), SExprNode(atom="B.Cu")],
                    ),
                    SExprNode(head="net", children=[SExprNode(atom=str(code))]),
                ],
            )
        )

    return SExprNode(head="kicad_pcb", children=children)


def _emit_footprint(fp: FootprintInstance, net_codes: dict[str, int]) -> SExprNode:
    kids: list[SExprNode] = [
        SExprNode(atom=fp.footprint_ref),
        SExprNode(
            head="layer",
            children=[SExprNode(atom=fp.placement.layer.value)],
        ),
        SExprNode(
            head="at",
            children=[
                SExprNode(atom=str(fp.placement.x)),
                SExprNode(atom=str(fp.placement.y)),
                SExprNode(atom=str(fp.placement.rotation_deg)),
            ],
        ),
        SExprNode(
            head="property",
            children=[
                SExprNode(atom="Reference"),
                SExprNode(atom=fp.reference),
            ],
        ),
        SExprNode(
            head="property",
            children=[
                SExprNode(atom="Value"),
                SExprNode(atom=fp.value or fp.reference),
            ],
        ),
        SExprNode(
            head="fp_text",
            children=[
                SExprNode(atom="reference"),
                SExprNode(atom=fp.reference),
                SExprNode(head="at", children=[SExprNode(atom="0"), SExprNode(atom="-2")]),
                SExprNode(head="layer", children=[SExprNode(atom="F.SilkS")]),
            ],
        ),
    ]
    for pad in fp.pads:
        pad_kids: list[SExprNode] = [
            SExprNode(atom=pad.number),
            SExprNode(atom="smd"),
            SExprNode(atom="rect"),
            SExprNode(
                head="at",
                children=[SExprNode(atom=str(pad.x)), SExprNode(atom=str(pad.y))],
            ),
            SExprNode(
                head="size",
                children=[SExprNode(atom=str(pad.width)), SExprNode(atom=str(pad.height))],
            ),
            SExprNode(
                head="layers",
                children=[
                    SExprNode(atom="F.Cu"),
                    SExprNode(atom="F.Paste"),
                    SExprNode(atom="F.Mask"),
                ],
            ),
        ]
        if pad.net_name:
            code = net_codes.get(pad.net_name, 0)
            pad_kids.append(
                SExprNode(
                    head="net",
                    children=[SExprNode(atom=str(code)), SExprNode(atom=pad.net_name)],
                )
            )
        kids.append(SExprNode(head="pad", children=pad_kids))
    return SExprNode(head="footprint", children=kids)


def emit_pcb_text(board: Board) -> str:
    return serialize_sexpr(emit_pcb_ast(board)) + "\n"


def write_pcb(board: Board, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(emit_pcb_text(board), encoding="utf-8")
    return out
