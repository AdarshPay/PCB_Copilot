"""Board-edge and power connector profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="GCT / Molex-compatible",
        orderable_mpn="USB4105-GF-A",
        functional_class=FunctionalClass.CONNECTOR,
        symbol_ref="Connector_USB:USB_C_Receptacle_USB2.0",
        footprint_ref="Connector_USB:USB_C_Receptacle_GCT_USB4105",
        pins=[
            Pin(number="A1", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="A4", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="A5", name="CC1", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_cc1", voltage_domain="5V"),
            Pin(number="A6", name="DP1", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dp", voltage_domain="3V3"),
            Pin(number="A7", name="DN1", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dm", voltage_domain="3V3"),
            Pin(number="A8", name="SBU1", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_sbu1"),
            Pin(number="A9", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="A12", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="B1", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="B4", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="B5", name="CC2", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_cc2", voltage_domain="5V"),
            Pin(number="B6", name="DP2", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dp", voltage_domain="3V3"),
            Pin(number="B7", name="DN2", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dm", voltage_domain="3V3"),
            Pin(number="B8", name="SBU2", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_sbu2"),
            Pin(number="B9", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="B12", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="S1", name="SHIELD", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="vbus", operator="lte", value=20, unit="V", notes="USB-PD capable shell; USB2.0 signal pins"),
        ],
        recommended_operating=[
            Constraint(name="vbus", operator="between", value=[4.75, 5.5], unit="V", notes="USB2.0 sink without PD"),
        ],
        supply_domains=["5V", "3V3", "GND"],
        required_support_components=[
            "cc1_rd_5k1_to_gnd_for_udevice",
            "cc2_rd_5k1_to_gnd_for_udevice",
            "vbus_bulk_10uF",
            "usb_esd_on_dp_dm",
        ],
        recommended_support_components=["shield_to_gnd_via_ferrite_or_direct"],
        boot_reset_config=[],
        interface_characteristics={
            "standard": "USB Type-C receptacle, USB 2.0 only (no SuperSpeed)",
            "orientation": "flip-able; DP/DN pairs shorted on PCB for USB2",
        },
        approved_reference_circuits=["usb-if:typec_usb2_device"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:usb4105",
                kind="datasheet",
                title="USB4105 USB Type-C Receptacle",
                uri="https://gct.co/files/drawings/usb4105.pdf",
                page=1,
                confidence=0.8,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Molex",
        orderable_mpn="105017-0001",
        functional_class=FunctionalClass.CONNECTOR,
        symbol_ref="Connector_USB:USB_Micro-B",
        footprint_ref="Connector_USB:USB_Micro-B_Molex_105017-0001",
        pins=[
            Pin(number="1", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="2", name="D-", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dm", voltage_domain="3V3"),
            Pin(number="3", name="D+", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dp", voltage_domain="3V3"),
            Pin(number="4", name="ID", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_id"),
            Pin(number="5", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="6", name="SHIELD", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="vbus", operator="lte", value=5.25, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vbus", operator="between", value=[4.75, 5.25], unit="V"),
        ],
        supply_domains=["5V", "GND"],
        required_support_components=["vbus_bulk_10uF", "usb_esd_on_dp_dm"],
        recommended_support_components=["id_nc_for_device_mode"],
        boot_reset_config=[],
        interface_characteristics={
            "standard": "USB 2.0 Micro-B receptacle",
            "current": "up to 1.8 A contact rating typical",
        },
        approved_reference_circuits=["molex:105017_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:105017-0001",
                kind="datasheet",
                title="Molex 105017 Micro-USB B Receptacle",
                uri="https://www.molex.com/pdm_docs/sd/1050170001_sd.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="JST",
        orderable_mpn="B2B-PH-K-S(LF)(SN)",
        functional_class=FunctionalClass.CONNECTOR,
        symbol_ref="Connector_JST:B2B-PH-K",
        footprint_ref="Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
        pins=[
            Pin(number="1", name="PIN1", electrical_role=ElectricalRole.PASSIVE, interface_role="pwr", voltage_domain="VIN"),
            Pin(number="2", name="PIN2", electrical_role=ElectricalRole.PASSIVE, interface_role="gnd", voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="contact_current", operator="lte", value=2.0, unit="A"),
            Constraint(name="voltage", operator="lte", value=100, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="contact_current", operator="lte", value=2.0, unit="A"),
        ],
        supply_domains=["VIN", "GND"],
        required_support_components=[],
        recommended_support_components=["strain_relief_or_adhesive_on_cable"],
        boot_reset_config=[],
        interface_characteristics={
            "series": "JST PH 2.0 mm pitch",
            "use": "2-pin power / battery input",
        },
        approved_reference_circuits=["jst:ph_series"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:b2b-ph-k",
                kind="datasheet",
                title="JST PH Series Connector",
                uri="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
]
