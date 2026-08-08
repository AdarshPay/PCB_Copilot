"""Build an unplaced Board skeleton from a Circuit IR Design."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design
from pcb_ai_pcb_ir.models import (
    Board,
    BoardNet,
    FootprintInstance,
    Outline,
    Pad,
    Placement,
    Point,
)


def schematic_design_to_board_skeleton(
    design: Design,
    *,
    board_id: str | None = None,
    outline_width: float = 50.0,
    outline_height: float = 40.0,
) -> Board:
    """Create footprints + nets from Design; placements start unplaced.

    Pads are assigned net names from design net endpoints. Pad geometry is a
    default SMD box unless profile-level detail is added later.
    """
    pin_nets: dict[tuple[str, str], str] = {}
    for net in design.nets:
        for ep in net.endpoints:
            pin_nets[(ep.component_ref, ep.pin_number)] = net.name

    footprints: list[FootprintInstance] = []
    for component in design.components:
        fp_ref = component.footprint_ref or f"Unknown:{component.reference}"
        pads = [
            Pad(
                number=pin.number,
                name=pin.name,
                net_name=pin_nets.get((component.reference, pin.number)),
                x=0.0 if i % 2 == 0 else 1.5,
                y=(i // 2) * 1.0,
                width=0.8,
                height=0.8,
            )
            for i, pin in enumerate(component.pins)
        ]
        # Default courtyard from pad span or 5mm box.
        footprints.append(
            FootprintInstance(
                reference=component.reference,
                footprint_ref=fp_ref,
                value=component.value,
                placement=Placement(placed=False),
                pads=pads,
                courtyard_width=max(5.0, 2.0 + len(component.pins) * 0.5),
                courtyard_height=5.0,
                uuid=component.uuid,
            )
        )

    nets = [BoardNet(name=n.name) for n in design.nets if n.name]

    return Board(
        id=board_id or f"board:{design.id}",
        design_id=design.id,
        name=design.name,
        outline=Outline(
            width=outline_width,
            height=outline_height,
            origin=Point(x=0.0, y=0.0),
        ),
        footprints=footprints,
        nets=nets,
    )
