"""Debug / programming header profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Samtec",
        orderable_mpn="FTSH-105-01-L-DV",
        functional_class=FunctionalClass.PROGRAMMING,
        symbol_ref="Connector_PinHeader_2.00mm:PinHeader_2x05_P2.00mm_Vertical_SMD",
        footprint_ref="Connector_PinHeader_2.00mm:PinHeader_2x05_P2.00mm_Vertical_SMD",
        pins=[
            Pin(number="1", name="VTREF", electrical_role=ElectricalRole.POWER_OUT, interface_role="swd_vref", voltage_domain="3V3"),
            Pin(number="2", name="SWDIO", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="swd_dio", voltage_domain="3V3"),
            Pin(number="3", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="4", name="SWCLK", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="swd_clk", voltage_domain="3V3"),
            Pin(number="5", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="6", name="SWO", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="swo", voltage_domain="3V3"),
            Pin(number="7", name="KEY", electrical_role=ElectricalRole.NO_CONNECT, interface_role="key"),
            Pin(number="8", name="NC", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="9", name="GNDDetect", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="10", name="nRESET", electrical_role=ElectricalRole.RESET, interface_role="nrst", voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="pin_voltage", operator="lte", value=3.6, unit="V", notes="target IO rail limited"),
        ],
        recommended_operating=[
            Constraint(name="vtref", operator="between", value=[1.8, 3.3], unit="V"),
        ],
        supply_domains=["3V3", "GND"],
        required_support_components=["swdio_pullup_10k_to_vtref", "nrst_pullup_10k"],
        recommended_support_components=["series_22R_on_swdio_swclk"],
        boot_reset_config=[
            "ARM 10-pin Cortex Debug Connector pinout (Samtec FTSH-105)",
            "Pin 7 keyed / removed on mating cable",
        ],
        interface_characteristics={
            "standard": "ARM Cortex 10-pin 1.27 mm debug",
            "protocols": "SWD + optional SWO",
        },
        approved_reference_circuits=["arm:coresight_10pin"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:ftsh-105",
                kind="datasheet",
                title="Samtec FTSH-105 Micro Header",
                uri="https://suddendocs.samtec.com/prints/ftsh-1xx-xx-x-dv-x-xxx-mkt.pdf",
                page=1,
                confidence=0.8,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Tag-Connect",
        orderable_mpn="TC2030-IDC-NL",
        functional_class=FunctionalClass.PROGRAMMING,
        symbol_ref="Connector:Tag-Connect_TC2030",
        footprint_ref="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
        pins=[
            Pin(number="1", name="VCC", electrical_role=ElectricalRole.POWER_OUT, interface_role="swd_vref", voltage_domain="3V3"),
            Pin(number="2", name="SWDIO", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="swd_dio", voltage_domain="3V3"),
            Pin(number="3", name="nRESET", electrical_role=ElectricalRole.RESET, interface_role="nrst", voltage_domain="3V3"),
            Pin(number="4", name="SWCLK", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="swd_clk", voltage_domain="3V3"),
            Pin(number="5", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="6", name="SWO", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="swo", voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="pin_voltage", operator="lte", value=3.6, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[1.8, 3.3], unit="V"),
        ],
        supply_domains=["3V3", "GND"],
        required_support_components=["pcb_pads_per_tc2030_footprint", "swdio_pullup_10k"],
        recommended_support_components=["keepout_for_legged_probe_clearance"],
        boot_reset_config=["No-legs (NL) variant mates to plated pads; hold with clip or legs variant"],
        interface_characteristics={
            "standard": "Tag-Connect TC2030 6-pin SWD",
            "use": "space-saving programming / debug pads",
        },
        approved_reference_circuits=["tag-connect:tc2030_swd"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:tc2030",
                kind="datasheet",
                title="Tag-Connect TC2030 Plug-of-Nails",
                uri="https://www.tag-connect.com/wp-content/uploads/sites/3/downloads/2012/08/TC2030-IDC-NL.pdf",
                page=1,
                confidence=0.8,
            )
        ],
    ),
]
