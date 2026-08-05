"""USB-UART and interface bridge profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Silicon Labs",
        orderable_mpn="CP2102",
        functional_class=FunctionalClass.INTERFACE_BRIDGE,
        symbol_ref="Interface_USB:CP2102",
        footprint_ref="Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="DCD", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_dcd", voltage_domain="3V3"),
            Pin(number="2", name="RI", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_ri", voltage_domain="3V3"),
            Pin(number="3", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="4", name="D+", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dp", voltage_domain="3V3"),
            Pin(number="5", name="D-", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dm", voltage_domain="3V3"),
            Pin(number="6", name="VDD", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="7", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="8", name="REGIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="9", name="VBUS", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="10", name="RST", electrical_role=ElectricalRole.RESET, voltage_domain="3V3"),
            Pin(
                number="11",
                name="SUSPEND",
                electrical_role=ElectricalRole.DIGITAL_OUT,
                interface_role="usb_suspend",
                voltage_domain="3V3",
            ),
            Pin(number="25", name="TXD", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_tx", voltage_domain="3V3"),
            Pin(number="26", name="RXD", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_rx", voltage_domain="3V3"),
            Pin(number="27", name="RTS", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_rts", voltage_domain="3V3"),
            Pin(number="28", name="CTS", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_cts", voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vbus", operator="lte", value=5.8, unit="V"),
            Constraint(name="vdd", operator="lte", value=4.2, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vdd", operator="between", value=[3.0, 3.6], unit="V"),
            Constraint(name="vbus", operator="between", value=[4.0, 5.25], unit="V"),
        ],
        supply_domains=["5V", "3V3", "GND"],
        required_support_components=[
            "regin_bypass_1uF_to_4u7",
            "vdd_decoupling_1uF",
            "vbus_decoupling_1uF",
            "usb_esd_protection",
        ],
        recommended_support_components=["rst_pullup_4k7", "uart_series_22R"],
        boot_reset_config=["RST active-low; internal POR also present"],
        interface_characteristics={
            "usb": "USB 2.0 full-speed device",
            "uart": "up to 1 Mbaud; CMOS levels vs VDD",
        },
        approved_reference_circuits=["silabs:cp2102_typical_connection"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:cp2102",
                kind="datasheet",
                title="CP2102 USB to UART Bridge",
                uri="https://www.silabs.com/documents/public/data-sheets/cp2102-datasheet.pdf",
                page=1,
                confidence=0.85,
            ),
            EvidenceRef(
                id="fixture:uart_bridge",
                kind="fixture",
                title="Golden USB-UART bridge uses CP2102",
                confidence=1.0,
            ),
        ],
    ),
]
