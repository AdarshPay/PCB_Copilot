"""Crystal and related passive support profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Abracon",
        orderable_mpn="ABM8G-12.000MHZ-18-D2Y-T",
        functional_class=FunctionalClass.PASSIVE,
        symbol_ref="Device:Crystal",
        footprint_ref="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
        pins=[
            Pin(number="1", name="X1", electrical_role=ElectricalRole.PASSIVE, interface_role="xtal_in", voltage_domain="XTAL"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="X2", electrical_role=ElectricalRole.PASSIVE, interface_role="xtal_out", voltage_domain="XTAL"),
            Pin(number="4", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="drive_level", operator="lte", value=100, unit="uW"),
            Constraint(name="storage_temp", operator="between", value=[-55, 125], unit="C"),
        ],
        recommended_operating=[
            Constraint(name="frequency", operator="eq", value=12.0, unit="MHz"),
            Constraint(name="load_capacitance", operator="eq", value=18, unit="pF"),
            Constraint(name="ambient_temp", operator="between", value=[-40, 85], unit="C"),
        ],
        supply_domains=["XTAL", "GND"],
        required_support_components=["load_cap_cl1", "load_cap_cl2"],
        recommended_support_components=["series_damping_resistor_if_overdrive"],
        boot_reset_config=[],
        interface_characteristics={
            "frequency": "12.000 MHz",
            "load_cap": "18 pF",
            "package": "3.2 x 2.5 mm 4-pad",
            "use": "MCU HSE / RP2040 XIN-XOUT reference",
        },
        approved_reference_circuits=["abracon:abm8g_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:abm8g-12",
                kind="datasheet",
                title="ABM8G Ceramic SMD Crystal",
                uri="https://abracon.com/Resonators/ABM8G.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
]
