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

# Named first-pack rules covered by mutation tests (Days 8-9 + Day 30 expansions).
FIRST_PACK_RULE_IDS: frozenset[str] = frozenset(
    {
        "struct.unique_references",
        "struct.pin_existence",
        "struct.footprint_presence",
        "elec.output_conflict",
        "elec.undriven_input",
        "elec.power_source",
        "elec.open_drain_pullup",
        "elec.voltage_domain",
        "elec.polarity",
    }
)

# Classes that must declare footprint_ref (mirrors verification FOOTPRINT_REQUIRED_CLASSES).
_FOOTPRINT_REQUIRED: frozenset[FunctionalClass] = frozenset(
    {
        FunctionalClass.MCU,
        FunctionalClass.SENSOR,
        FunctionalClass.REGULATOR_LDO,
        FunctionalClass.REGULATOR_BUCK,
        FunctionalClass.TRANSCEIVER,
        FunctionalClass.CONNECTOR,
        FunctionalClass.PROTECTION,
        FunctionalClass.INTERFACE_BRIDGE,
        FunctionalClass.PROGRAMMING,
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


def mutate_missing_footprint(design: Design) -> Design:
    """Clear footprint_ref on a required-class part, or add an MCU without one."""
    mutant = design.model_copy(deep=True)
    for component in mutant.components:
        if component.functional_class in _FOOTPRINT_REQUIRED:
            component.footprint_ref = None
            return mutant
    mutant.components.append(
        Component(
            reference="U_MUT_FP",
            value="MUT_NO_FP",
            functional_class=FunctionalClass.MCU,
            footprint_ref=None,
            pins=[
                Pin(number="1", name="NC", electrical_role=ElectricalRole.UNSPECIFIED),
            ],
            uuid=str(uuid4()),
        )
    )
    return mutant


def mutate_output_conflict(design: Design) -> Design:
    """Tie a second digital output onto an existing driven signal net."""
    mutant = design.model_copy(deep=True)
    driver = Component(
        reference="U_MUT_OUT",
        value="MUT_DRIVER",
        functional_class=FunctionalClass.MCU,
        footprint_ref="Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm",
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


def mutate_undriven_enable(design: Design) -> Design:
    """Add a required enable input that is not attached to any net.

    Single-fault variant of undriven_input covering ElectricalRole.ENABLE
    (same elec.undriven_input rule; distinct fault injection shape).
    """
    mutant = design.model_copy(deep=True)
    mutant.components.append(
        Component(
            reference="U_MUT_EN",
            value="MUT_ENABLE",
            functional_class=FunctionalClass.OTHER,
            pins=[
                Pin(number="1", name="EN", electrical_role=ElectricalRole.ENABLE),
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


def mutate_missing_open_drain_pullup(design: Design) -> Design:
    """Add an open-drain pin on a bus net with no passive pull-up to power."""
    mutant = design.model_copy(deep=True)
    mutant.components.append(
        Component(
            reference="U_MUT_OD",
            value="MUT_OD",
            functional_class=FunctionalClass.OTHER,
            pins=[
                Pin(number="1", name="OD", electrical_role=ElectricalRole.OPEN_DRAIN),
            ],
            uuid=str(uuid4()),
        )
    )
    mutant.nets.append(
        Net(
            name="NET_MUT_OD",
            net_class=NetClass.BUS,
            protocol="i2c",
            endpoints=[Endpoint(component_ref="U_MUT_OD", pin_number="1")],
            uuid=str(uuid4()),
        )
    )
    return mutant


def mutate_voltage_domain_conflict(design: Design) -> Design:
    """Place two declared voltage domains on the same signal net."""
    mutant = design.model_copy(deep=True)
    mutant.components.extend(
        [
            Component(
                reference="U_MUT_VD_A",
                value="MUT_VD_A",
                functional_class=FunctionalClass.OTHER,
                pins=[
                    Pin(
                        number="1",
                        name="IO",
                        electrical_role=ElectricalRole.DIGITAL_BIDIR,
                        voltage_domain="3V3",
                    ),
                ],
                uuid=str(uuid4()),
            ),
            Component(
                reference="U_MUT_VD_B",
                value="MUT_VD_B",
                functional_class=FunctionalClass.OTHER,
                pins=[
                    Pin(
                        number="1",
                        name="IO",
                        electrical_role=ElectricalRole.DIGITAL_BIDIR,
                        voltage_domain="5V",
                    ),
                ],
                uuid=str(uuid4()),
            ),
        ]
    )
    mutant.nets.append(
        Net(
            name="NET_MUT_VD",
            net_class=NetClass.SIGNAL,
            endpoints=[
                Endpoint(component_ref="U_MUT_VD_A", pin_number="1"),
                Endpoint(component_ref="U_MUT_VD_B", pin_number="1"),
            ],
            uuid=str(uuid4()),
        )
    )
    return mutant


def mutate_reversed_polarity(design: Design) -> Design:
    """Add a polarized capacitor with + on ground and - on a power rail."""
    mutant = design.model_copy(deep=True)
    power_net = next((n for n in mutant.nets if n.net_class == NetClass.POWER), None)
    ground_net = next((n for n in mutant.nets if n.net_class == NetClass.GROUND), None)
    if power_net is None or ground_net is None:
        raise ValueError("reversed_polarity mutation needs power and ground nets")

    mutant.components.append(
        Component(
            reference="C_MUT_POL",
            value="10uF",
            functional_class=FunctionalClass.PASSIVE,
            pins=[
                Pin(number="1", name="+", electrical_role=ElectricalRole.PASSIVE),
                Pin(number="2", name="-", electrical_role=ElectricalRole.PASSIVE),
            ],
            attributes={
                "polarized": True,
                "positive_pin": "1",
                "negative_pin": "2",
            },
            uuid=str(uuid4()),
        )
    )
    # Reversed: positive → ground, negative → power.
    ground_net.endpoints.append(Endpoint(component_ref="C_MUT_POL", pin_number="1"))
    power_net.endpoints.append(Endpoint(component_ref="C_MUT_POL", pin_number="2"))
    return mutant
