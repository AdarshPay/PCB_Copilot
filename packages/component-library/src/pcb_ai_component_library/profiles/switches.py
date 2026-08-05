"""MOSFET load-switch / power-path discrete profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Alpha & Omega Semiconductor",
        orderable_mpn="AO3400A",
        functional_class=FunctionalClass.OTHER,
        symbol_ref="Device:Q_NMOS_GSD",
        footprint_ref="Package_TO_SOT_SMD:SOT-23",
        pins=[
            Pin(number="1", name="G", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="gate", voltage_domain="3V3"),
            Pin(number="2", name="S", electrical_role=ElectricalRole.POWER_IN, interface_role="source", voltage_domain="GND"),
            Pin(number="3", name="D", electrical_role=ElectricalRole.POWER_OUT, interface_role="drain", voltage_domain="LOAD"),
        ],
        absolute_maximum=[
            Constraint(name="vds", operator="lte", value=30, unit="V"),
            Constraint(name="vgs", operator="between", value=[-12, 12], unit="V"),
            Constraint(name="id_continuous", operator="lte", value=5.8, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vgs_on", operator="between", value=[2.5, 10], unit="V", notes="logic-level gate"),
            Constraint(name="id", operator="lte", value=3.0, unit="A", notes="board thermal limited"),
        ],
        supply_domains=["LOAD", "GND", "3V3"],
        required_support_components=["gate_series_100R", "gate_pulldown_100k"],
        recommended_support_components=["flyback_diode_if_inductive_load"],
        boot_reset_config=["Low-side N-MOS load switch; gate high turns load on when source at GND"],
        interface_characteristics={
            "type": "N-channel enhancement MOSFET",
            "rds_on": "~33 mOhm typ at Vgs=10 V",
            "use": "low-side load switch / power path",
        },
        approved_reference_circuits=["aos:ao3400_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:ao3400a",
                kind="datasheet",
                title="AO3400A 30V N-Channel MOSFET",
                uri="https://www.aosmd.com/res/data_sheets/AO3400A.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="TPS22918DBVR",
        functional_class=FunctionalClass.OTHER,
        symbol_ref="Device:Load_Switch",
        footprint_ref="Package_TO_SOT_SMD:SOT-23-6",
        pins=[
            Pin(number="1", name="VIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="ON", electrical_role=ElectricalRole.ENABLE, voltage_domain="3V3"),
            Pin(number="4", name="QOD", electrical_role=ElectricalRole.PASSIVE, interface_role="quick_output_discharge"),
            Pin(number="5", name="CT", electrical_role=ElectricalRole.PASSIVE, interface_role="slew_cap"),
            Pin(number="6", name="VOUT", electrical_role=ElectricalRole.POWER_OUT, voltage_domain="VOUT"),
        ],
        absolute_maximum=[
            Constraint(name="vin", operator="lte", value=6.0, unit="V"),
            Constraint(name="iout", operator="lte", value=2.0, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vin", operator="between", value=[1.0, 5.5], unit="V"),
            Constraint(name="iout", operator="lte", value=2.0, unit="A"),
        ],
        supply_domains=["VIN", "VOUT", "GND"],
        required_support_components=["input_cap_1uF", "output_cap_1uF"],
        recommended_support_components=["ct_cap_for_slew", "qod_resistor_optional"],
        boot_reset_config=["ON high enables VOUT; CT sets rise time"],
        interface_characteristics={
            "type": "integrated PFET load switch",
            "rds_on": "~52 mOhm typ at 5 V",
            "features": "controlled slew + optional QOD",
        },
        approved_reference_circuits=["ti:tps22918_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:tps22918",
                kind="datasheet",
                title="TPS22918 5.5-V 2-A Load Switch",
                uri="https://www.ti.com/lit/ds/symlink/tps22918.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
]
