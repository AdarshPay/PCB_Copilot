"""ESD and reverse-polarity protection profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="STMicroelectronics",
        orderable_mpn="USBLC6-2SC6",
        functional_class=FunctionalClass.PROTECTION,
        symbol_ref="Power_Protection:USBLC6-2SC6",
        footprint_ref="Package_TO_SOT_SMD:SOT-23-6",
        pins=[
            Pin(number="1", name="I/O1", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_dp", voltage_domain="5V"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="I/O2", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_dm", voltage_domain="5V"),
            Pin(number="4", name="I/O2", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_dm", voltage_domain="5V"),
            Pin(number="5", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="6", name="I/O1", electrical_role=ElectricalRole.PASSIVE, interface_role="usb_dp", voltage_domain="5V"),
        ],
        absolute_maximum=[
            Constraint(name="vbus", operator="lte", value=6.0, unit="V"),
            Constraint(name="peak_pulse_current_8_20us", operator="lte", value=5, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vbus", operator="between", value=[0, 5.25], unit="V"),
            Constraint(name="working_voltage_io", operator="lte", value=5.0, unit="V"),
        ],
        supply_domains=["5V", "GND"],
        required_support_components=[],
        recommended_support_components=["place_close_to_usb_connector"],
        boot_reset_config=[],
        interface_characteristics={
            "channels": "2 data lines + VBUS",
            "capacitance": "~3.5 pF typical per I/O",
            "standard": "IEC 61000-4-2 Level 4",
        },
        approved_reference_circuits=["st:usblc6_usb_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:usblc6-2sc6",
                kind="datasheet",
                title="USBLC6-2 Very low capacitance ESD protection",
                uri="https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Nexperia",
        orderable_mpn="PESD5V0S1UB",
        functional_class=FunctionalClass.PROTECTION,
        symbol_ref="Device:D_TVS",
        footprint_ref="Package_TO_SOT_SMD:SOD-523",
        pins=[
            Pin(number="1", name="A", electrical_role=ElectricalRole.PASSIVE, interface_role="tvs_anode", voltage_domain="SIGNAL"),
            Pin(number="2", name="K", electrical_role=ElectricalRole.PASSIVE, interface_role="tvs_cathode", voltage_domain="SIGNAL"),
        ],
        absolute_maximum=[
            Constraint(name="peak_pulse_power_8_20us", operator="lte", value=260, unit="W"),
            Constraint(name="vrwm", operator="eq", value=5.0, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vrwm", operator="lte", value=5.0, unit="V"),
            Constraint(name="ambient_temp", operator="between", value=[-65, 150], unit="C"),
        ],
        supply_domains=["SIGNAL", "GND"],
        required_support_components=[],
        recommended_support_components=["place_at_connector_entry"],
        boot_reset_config=[],
        interface_characteristics={
            "type": "unidirectional TVS",
            "clamping": "suitable for 5 V signal/rail ESD",
        },
        approved_reference_circuits=["nexperia:pesd5v0_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:pesd5v0s1ub",
                kind="datasheet",
                title="PESD5V0S1UB ESD protection diode",
                uri="https://assets.nexperia.com/documents/data-sheet/PESD5V0S1UB.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Littelfuse",
        orderable_mpn="SMBJ5.0A",
        functional_class=FunctionalClass.PROTECTION,
        symbol_ref="Device:D_TVS",
        footprint_ref="Package_TO_SOT_SMD:D_SMB",
        pins=[
            Pin(number="1", name="A", electrical_role=ElectricalRole.PASSIVE, interface_role="tvs_anode", voltage_domain="VIN"),
            Pin(number="2", name="K", electrical_role=ElectricalRole.PASSIVE, interface_role="tvs_cathode", voltage_domain="VIN"),
        ],
        absolute_maximum=[
            Constraint(name="peak_pulse_power_10_1000us", operator="lte", value=600, unit="W"),
            Constraint(name="vrwm", operator="eq", value=5.0, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vrwm", operator="lte", value=5.0, unit="V"),
            Constraint(name="ambient_temp", operator="between", value=[-65, 150], unit="C"),
        ],
        supply_domains=["VIN", "GND"],
        required_support_components=[],
        recommended_support_components=[
            "series_fuse_or_ptc_for_reverse_polarity_survival",
            "orient_cathode_to_protected_rail",
        ],
        boot_reset_config=[],
        interface_characteristics={
            "type": "unidirectional 600 W TVS",
            "use": "input rail surge / reverse-polarity clamp aid",
        },
        approved_reference_circuits=["littelfuse:smbj_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:smbj5.0a",
                kind="datasheet",
                title="SMBJ Transient Voltage Suppression Diode",
                uri="https://www.littelfuse.com/media?resourcetype=datasheets&itemid=3d5a0c9e-3d7a-4c3a-9f0b-0f0f0f0f0f0f&filename=littelfuse-smbj-datasheet",
                page=1,
                confidence=0.7,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="TPD2E001DRLR",
        functional_class=FunctionalClass.PROTECTION,
        symbol_ref="Power_Protection:TPD2E001",
        footprint_ref="Package_TO_SOT_SMD:SOT-553",
        pins=[
            Pin(number="1", name="IO1", electrical_role=ElectricalRole.PASSIVE, interface_role="esd_io1", voltage_domain="SIGNAL"),
            Pin(number="2", name="IO2", electrical_role=ElectricalRole.PASSIVE, interface_role="esd_io2", voltage_domain="SIGNAL"),
            Pin(number="3", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="4", name="VCC", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="5", name="NC", electrical_role=ElectricalRole.NO_CONNECT),
        ],
        absolute_maximum=[
            Constraint(name="vcc", operator="lte", value=5.5, unit="V"),
            Constraint(name="io_voltage", operator="between", value=[-0.5, 5.5], unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[0.9, 5.5], unit="V"),
        ],
        supply_domains=["5V", "SIGNAL", "GND"],
        required_support_components=["vcc_decoupling_100nF"],
        recommended_support_components=["place_at_connector_entry"],
        boot_reset_config=[],
        interface_characteristics={
            "channels": "2-line ESD array",
            "capacitance": "~1.5 pF typical",
            "standard": "IEC 61000-4-2 Level 4",
            "use": "USB / UART / GPIO ESD",
        },
        approved_reference_circuits=["ti:tpd2e001_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:tpd2e001",
                kind="datasheet",
                title="TPD2E001 Low-Capacitance ESD Protection",
                uri="https://www.ti.com/lit/ds/symlink/tpd2e001.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
]
