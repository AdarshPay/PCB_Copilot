"""CAN and RS-485 transceiver profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="TCAN1042HDRQ1",
        functional_class=FunctionalClass.TRANSCEIVER,
        symbol_ref="Interface_CAN_LIN:TCAN1042H",
        footprint_ref="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="TXD", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="can_tx", voltage_domain="3V3"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="VCC", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="4", name="RXD", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="can_rx", voltage_domain="3V3"),
            Pin(number="5", name="VIO", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="6", name="CANL", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="can_l", voltage_domain="CAN"),
            Pin(number="7", name="CANH", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="can_h", voltage_domain="CAN"),
            Pin(number="8", name="STB", electrical_role=ElectricalRole.ENABLE, interface_role="standby", voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vcc", operator="lte", value=7.0, unit="V"),
            Constraint(name="can_bus_voltage", operator="between", value=[-58, 58], unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[4.5, 5.5], unit="V"),
            Constraint(name="vio", operator="between", value=[2.8, 5.5], unit="V"),
        ],
        supply_domains=["5V", "3V3", "CAN", "GND"],
        required_support_components=["vcc_decoupling_100nF", "can_termination_120R_when_end_node"],
        recommended_support_components=["common_mode_choke", "esd_tvs_on_canh_canl", "stb_pulldown_for_normal_mode"],
        boot_reset_config=["STB low = normal mode; STB high = standby"],
        interface_characteristics={
            "protocol": "CAN FD up to 5 Mbps",
            "io_levels": "VIO-referenced TXD/RXD for 3.3 V MCU",
        },
        approved_reference_circuits=["ti:tcan1042_typical_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:tcan1042h",
                kind="datasheet",
                title="TCAN1042H Automotive Fault-Protected CAN Transceiver",
                uri="https://www.ti.com/lit/ds/symlink/tcan1042h-q1.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="SN65HVD230DR",
        functional_class=FunctionalClass.TRANSCEIVER,
        symbol_ref="Interface_CAN_LIN:SN65HVD230",
        footprint_ref="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="D", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="can_tx", voltage_domain="3V3"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="VCC", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="4", name="R", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="can_rx", voltage_domain="3V3"),
            Pin(number="5", name="VREF", electrical_role=ElectricalRole.ANALOG_OUT, interface_role="vref", voltage_domain="3V3"),
            Pin(number="6", name="CANL", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="can_l", voltage_domain="CAN"),
            Pin(number="7", name="CANH", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="can_h", voltage_domain="CAN"),
            Pin(number="8", name="Rs", electrical_role=ElectricalRole.PASSIVE, interface_role="slope_control"),
        ],
        absolute_maximum=[
            Constraint(name="vcc", operator="lte", value=6.0, unit="V"),
            Constraint(name="can_bus_voltage", operator="between", value=[-4, 16], unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[3.0, 3.6], unit="V"),
        ],
        supply_domains=["3V3", "CAN", "GND"],
        required_support_components=["vcc_decoupling_100nF", "can_termination_120R_when_end_node"],
        recommended_support_components=["rs_47k_for_slew_limiting", "esd_protection_can"],
        boot_reset_config=["Rs to GND = high speed; Rs via resistor = slope control; Rs high = standby"],
        interface_characteristics={
            "protocol": "CAN 2.0B up to 1 Mbps",
            "supply": "3.3 V single supply",
        },
        approved_reference_circuits=["ti:sn65hvd230_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:sn65hvd230",
                kind="datasheet",
                title="SN65HVD230 3.3-V CAN Transceiver",
                uri="https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Maxim Integrated / Analog Devices",
        orderable_mpn="MAX485ESA+",
        functional_class=FunctionalClass.TRANSCEIVER,
        symbol_ref="Interface_UART:MAX485",
        footprint_ref="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="RO", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_rx", voltage_domain="5V"),
            Pin(number="2", name="RE", electrical_role=ElectricalRole.ENABLE, interface_role="receiver_enable", voltage_domain="5V"),
            Pin(number="3", name="DE", electrical_role=ElectricalRole.ENABLE, interface_role="driver_enable", voltage_domain="5V"),
            Pin(number="4", name="DI", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_tx", voltage_domain="5V"),
            Pin(number="5", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="6", name="A", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="rs485_a", voltage_domain="RS485"),
            Pin(number="7", name="B", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="rs485_b", voltage_domain="RS485"),
            Pin(number="8", name="VCC", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
        ],
        absolute_maximum=[
            Constraint(name="vcc", operator="lte", value=12, unit="V"),
            Constraint(name="a_b_voltage", operator="between", value=[-8, 12.5], unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[4.75, 5.25], unit="V"),
            Constraint(name="data_rate", operator="lte", value=2.5, unit="Mbps"),
        ],
        supply_domains=["5V", "RS485", "GND"],
        required_support_components=["vcc_decoupling_100nF", "failsafe_bias_or_termination_when_end_node"],
        recommended_support_components=["esd_tvs_on_a_b", "series_10R_on_a_b"],
        boot_reset_config=[
            "RE active-low enables receiver",
            "DE high enables driver; tie RE/DE for half-duplex direction control",
        ],
        interface_characteristics={
            "protocol": "RS-485 / RS-422 half-duplex",
            "unit_load": "1 UL; up to 32 nodes",
        },
        approved_reference_circuits=["max:max485_typical_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:max485",
                kind="datasheet",
                title="MAX485 RS-485/RS-422 Transceiver",
                uri="https://www.analog.com/media/en/technical-documentation/data-sheets/MAX481-MAX491.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
]
