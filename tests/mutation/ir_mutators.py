"""Single-fault Circuit IR mutators for deterministic rule tests.

Each mutator injects exactly one fault class into a deep copy of a clean design.
"""

from __future__ import annotations

from uuid import uuid4

from pcb_ai_circuit_ir.models import (
    Component,
    Design,
    ElectricalRole,
    Endpoint,
    FunctionalClass,
    Net,
    NetClass,
    Pin,
)

# Named first-pack rules covered by Days 8-9 mutation tests.
FIRST_PACK_RULE_IDS: frozenset[str] = frozenset(
    {
        "struct.unique_references",
        "struct.pin_existence",
        "elec.output_conflict",
        "elec.undriven_input",
        "elec.power_source",
    }
)


def mutate_duplicate_reference(design: Design) -> Design:
    """Inject an unconnected clone that reuses an existing reference designator.

    Renaming a wired component would also orphan net endpoints and trip
    pin_existence; cloning keeps this a single-fault mutation.
    """
    mutant = design.model_copy(deep=True)
    if not mutant.components:
        raise ValueError("duplicate_reference mutation needs at least one component")
    original = mutant.components[0]
    mutant.components.append(
        Component(
            reference=original.reference,
            value=original.value,
            functional_class=original.functional_class,
            symbol_ref=original.symbol_ref,
            footprint_ref=original.footprint_ref,
            pins=[
                Pin(
                    number=pin.number,
                    name=pin.name,
                    electrical_role=pin.electrical_role,
                )
                for pin in original.pins
            ],
            uuid=str(uuid4()),
        )
    )
    return mutant


def mutate_missing_pin(design: Design) -> Design:
    """Point a net endpoint at a pin number that does not exist on the component."""
    mutant = design.model_copy(deep=True)
    if not mutant.nets or not mutant.nets[0].endpoints:
        raise ValueError("missing_pin mutation needs a net with an endpoint")
    mutant.nets[0].endpoints[0].pin_number = "999"
    return mutant


def mutate_output_conflict(design: Design) -> Design:
    """Tie a second digital output onto an existing driven signal net."""
    mutant = design.model_copy(deep=True)
    driver = Component(
        reference="U_MUT_OUT",
        value="MUT_DRIVER",
        functional_class=FunctionalClass.MCU,
        pins=[
            Pin(number="1", name="OUT", electrical_role=ElectricalRole.DIGITAL_OUT),
        ],
        uuid=str(uuid4()),
    )
    mutant.components.append(driver)

    # Prefer a clean signal/bus net; fall back to creating one tied to a passive pin.
    target: Net | None = next(
        (n for n in mutant.nets if n.net_class in {NetClass.SIGNAL, NetClass.BUS}),
        None,
    )
    if target is None:
        if not mutant.components or not mutant.components[0].pins:
            raise ValueError("output_conflict mutation needs a component pin to attach")
        host = mutant.components[0]
        target = Net(
            name="NET_MUT_FIGHT",
            net_class=NetClass.SIGNAL,
            endpoints=[Endpoint(component_ref=host.reference, pin_number=host.pins[0].number)],
            uuid=str(uuid4()),
        )
        # Ensure the host pin is an output so two drivers conflict.
        host.pins[0].electrical_role = ElectricalRole.DIGITAL_OUT
        mutant.nets.append(target)
    else:
        # Ensure at least one existing endpoint is a driven output.
        first = target.endpoints[0]
        for component in mutant.components:
            if component.reference != first.component_ref:
                continue
            for pin in component.pins:
                if pin.number == first.pin_number:
                    pin.electrical_role = ElectricalRole.DIGITAL_OUT
                    break

    target.endpoints.append(Endpoint(component_ref=driver.reference, pin_number="1"))
    return mutant


def mutate_undriven_input(design: Design) -> Design:
    """Add a required digital input that is not attached to any net."""
    mutant = design.model_copy(deep=True)
    mutant.components.append(
        Component(
            reference="U_MUT_IN",
            value="MUT_INPUT",
            functional_class=FunctionalClass.OTHER,
            pins=[
                Pin(number="1", name="IN", electrical_role=ElectricalRole.DIGITAL_IN),
            ],
            uuid=str(uuid4()),
        )
    )
    return mutant


def mutate_missing_power_source(design: Design) -> Design:
    """Attach a power-input pin to a non-power net with no power_out driver."""
    mutant = design.model_copy(deep=True)
    mutant.components.append(
        Component(
            reference="U_MUT_PWR",
            value="MUT_LOAD",
            functional_class=FunctionalClass.OTHER,
            pins=[
                Pin(number="1", name="VDD", electrical_role=ElectricalRole.POWER_IN),
            ],
            uuid=str(uuid4()),
        )
    )
    mutant.nets.append(
        Net(
            name="NET_MUT_NO_SOURCE",
            net_class=NetClass.SIGNAL,
            endpoints=[Endpoint(component_ref="U_MUT_PWR", pin_number="1")],
            uuid=str(uuid4()),
        )
    )
    return mutant
