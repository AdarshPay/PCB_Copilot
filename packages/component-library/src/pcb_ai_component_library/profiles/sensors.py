"""I2C sensor family profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="TMP117",
        functional_class=FunctionalClass.SENSOR,
        symbol_ref="Sensor_Temperature:TMP117",
        footprint_ref="Package_TO_SOT_SMD:SOT-563",
        pins=[
            Pin(
                number="1",
                name="SCL",
                electrical_role=ElectricalRole.OPEN_DRAIN,
                interface_role="i2c_scl",
                voltage_domain="3V3",
            ),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(
                number="3",
                name="ALERT",
                electrical_role=ElectricalRole.OPEN_DRAIN,
                interface_role="alert",
                voltage_domain="3V3",
            ),
            Pin(
                number="4",
                name="ADD0",
                electrical_role=ElectricalRole.DIGITAL_IN,
                interface_role="addr_select",
                voltage_domain="3V3",
            ),
            Pin(number="5", name="V+", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(
                number="6",
                name="SDA",
                electrical_role=ElectricalRole.OPEN_DRAIN,
                interface_role="i2c_sda",
                voltage_domain="3V3",
            ),
        ],
        absolute_maximum=[
            Constraint(name="vplus", operator="lte", value=6.0, unit="V"),
            Constraint(name="operating_temp", operator="between", value=[-55, 150], unit="C"),
        ],
        recommended_operating=[
            Constraint(name="vplus", operator="between", value=[1.8, 5.5], unit="V"),
            Constraint(name="ambient_temp", operator="between", value=[-55, 150], unit="C"),
        ],
        supply_domains=["3V3", "GND"],
        required_support_components=["i2c_pullup_sda_4k7", "i2c_pullup_scl_4k7", "decoupling_100nF_vplus"],
        recommended_support_components=["alert_pullup_10k"],
        boot_reset_config=["ADD0 strapping selects I2C address (GND/V+/SDA/SCL)"],
        interface_characteristics={
            "bus": "I2C up to 1 MHz",
            "default_address": "0x48 when ADD0=GND",
            "alert": "open-drain active-low",
        },
        approved_reference_circuits=["ti:tmp117_evm"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:tmp117",
                kind="datasheet",
                title="TMP117 High-Accuracy Digital Temperature Sensor",
                uri="https://www.ti.com/lit/ds/symlink/tmp117.pdf",
                page=1,
                confidence=0.85,
            ),
            EvidenceRef(
                id="fixture:i2c_sensor",
                kind="fixture",
                title="Golden MCU + I2C sensor uses TMP117",
                confidence=1.0,
            ),
        ],
    ),
    ComponentProfile(
        manufacturer="Bosch Sensortec",
        orderable_mpn="BME280",
        functional_class=FunctionalClass.SENSOR,
        symbol_ref="Sensor_Environmental:BME280",
        footprint_ref="Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering",
        pins=[
            Pin(number="1", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="2", name="CSB", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="spi_cs", voltage_domain="3V3"),
            Pin(
                number="3",
                name="SDO",
                electrical_role=ElectricalRole.DIGITAL_BIDIR,
                interface_role="i2c_addr_spi_miso",
                voltage_domain="3V3",
            ),
            Pin(number="4", name="SCK", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="i2c_scl", voltage_domain="3V3"),
            Pin(number="5", name="SDI", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="i2c_sda", voltage_domain="3V3"),
            Pin(number="6", name="VDDIO", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="7", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="8", name="VDD", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vdd", operator="lte", value=4.25, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vdd", operator="between", value=[1.71, 3.6], unit="V"),
            Constraint(name="vddio", operator="between", value=[1.2, 3.6], unit="V"),
        ],
        supply_domains=["3V3", "VDDIO", "GND"],
        required_support_components=["decoupling_100nF_vdd", "i2c_pullup_sda_4k7", "i2c_pullup_scl_4k7"],
        recommended_support_components=["decoupling_100nF_vddio"],
        boot_reset_config=["CSB high selects I2C; SDO selects address 0x76/0x77"],
        interface_characteristics={
            "bus": "I2C or SPI",
            "i2c_addresses": "0x76 (SDO=GND) or 0x77 (SDO=VDDIO)",
        },
        approved_reference_circuits=["bosch:bme280_app_note"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:bme280",
                kind="datasheet",
                title="BME280 Combined humidity and pressure sensor",
                uri="https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf",
                page=1,
                confidence=0.8,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="TDK InvenSense",
        orderable_mpn="ICM-20602",
        functional_class=FunctionalClass.SENSOR,
        symbol_ref="Sensor_Motion:ICM-20602",
        footprint_ref="Package_LGA:LGA-16_3x3mm_P0.5mm_Layout1x4mm",
        pins=[
            Pin(number="1", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="2", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="3", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="4", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="5", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="6", name="AUX_DA", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="aux_sda", voltage_domain="3V3"),
            Pin(number="7", name="RESERVED", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="8", name="VDDIO", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="9", name="AD0/SDO", electrical_role=ElectricalRole.DIGITAL_BIDIR, interface_role="i2c_addr", voltage_domain="3V3"),
            Pin(number="10", name="REGOUT", electrical_role=ElectricalRole.PASSIVE),
            Pin(number="11", name="FSYNC", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="fsync", voltage_domain="3V3"),
            Pin(number="12", name="INT", electrical_role=ElectricalRole.DIGITAL_OUT, interface_role="interrupt", voltage_domain="3V3"),
            Pin(number="13", name="VDD", electrical_role=ElectricalRole.POWER_IN, voltage_domain="3V3"),
            Pin(number="14", name="RESV", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(
                number="15",
                name="SCL/SCLK",
                electrical_role=ElectricalRole.OPEN_DRAIN,
                interface_role="i2c_scl",
                voltage_domain="3V3",
            ),
            Pin(
                number="16",
                name="SDA/SDI",
                electrical_role=ElectricalRole.OPEN_DRAIN,
                interface_role="i2c_sda",
                voltage_domain="3V3",
            ),
            Pin(number="17", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="vdd", operator="lte", value=4.0, unit="V"),
        ],
        recommended_operating=[
            Constraint(name="vdd", operator="between", value=[1.71, 3.45], unit="V"),
            Constraint(name="vddio", operator="between", value=[1.71, 3.45], unit="V"),
        ],
        supply_domains=["3V3", "VDDIO", "GND"],
        required_support_components=[
            "decoupling_100nF_vdd",
            "regout_bypass_100nF",
            "i2c_pullup_sda_4k7",
            "i2c_pullup_scl_4k7",
        ],
        recommended_support_components=["int_pullup_10k"],
        boot_reset_config=["AD0 selects I2C address 0x68/0x69"],
        interface_characteristics={
            "bus": "I2C up to 400 kHz or SPI up to 8 MHz",
            "axes": "3-axis gyro + 3-axis accel",
        },
        approved_reference_circuits=["tdk:icm20602_eval"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:icm-20602",
                kind="datasheet",
                title="ICM-20602 Datasheet",
                uri="https://invensense.tdk.com/wp-content/uploads/2016/10/DS-000176-ICM-20602-v1.1.pdf",
                page=1,
                confidence=0.75,
            )
        ],
    ),
]
