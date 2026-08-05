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
    ComponentProfile(
        manufacturer="WCH",
        orderable_mpn="CH340C",
        functional_class=FunctionalClass.INTERFACE_BRIDGE,
        symbol_ref="Interface_USB:CH340C",
        footprint_ref="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="2", name="TXD", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_tx", voltage_domain="3V3"),
            Pin(number="3", name="RXD", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_rx", voltage_domain="3V3"),
            Pin(number="4", name="V3", electrical_role=ElectricalRole.POWER_OUT, interface_role="reg_3v3", voltage_domain="3V3"),
            Pin(number="5", name="UD+", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dp", voltage_domain="3V3"),
            Pin(number="6", name="UD-", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="usb_dm", voltage_domain="3V3"),
            Pin(number="7", name="XI", electrical_role=ElectricalRole.CLOCK, interface_role="xtal_in", voltage_domain="3V3"),
            Pin(number="8", name="XO", electrical_role=ElectricalRole.CLOCK, interface_role="xtal_out", voltage_domain="3V3"),
            Pin(number="9", name="CTS", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_cts", voltage_domain="3V3"),
            Pin(number="10", name="DTR", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_dtr", voltage_domain="3V3"),
            Pin(number="11", name="RTS", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="uart_rts", voltage_domain="3V3"),
            Pin(number="12", name="R232", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="mode"),
            Pin(number="13", name="VCC", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="14", name="RI", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_ri", voltage_domain="3V3"),
            Pin(number="15", name="DSR", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_dsr", voltage_domain="3V3"),
            Pin(number="16", name="DCD", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="uart_dcd", voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vcc", operator="lte", value=5.5, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vcc", operator="between", value=[4.0, 5.3], unit="V", notes="5 V supply; V3 is internal 3.3 V"),
        ],
        supply_domains=["5V", "3V3", "GND"],
        required_support_components=[
            "vcc_decoupling_100nF",
            "v3_cap_100nF",
            "12mhz_crystal_with_load_caps",
            "usb_esd_protection",
        ],
        recommended_support_components=["uart_series_22R"],
        boot_reset_config=["CH340C integrates oscillator; XI/XO need 12 MHz crystal"],
        interface_characteristics={
            "usb": "USB 2.0 full-speed device",
            "uart": "up to 2 Mbaud; CMOS levels vs V3 rail",
        },
        approved_reference_circuits=["wch:ch340c_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:ch340c",
                kind="datasheet",
                title="CH340C USB to Serial Chip",
                uri="https://www.wch-ic.com/downloads/CH340DS1_PDF.html",
                page=1,
                confidence=0.75,
            )
        ],
    ),
]
