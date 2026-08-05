"""LDO and buck regulator profiles."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Constraint, ElectricalRole, EvidenceRef, FunctionalClass, Pin

from pcb_ai_component_library.models import ComponentProfile

PROFILES: list[ComponentProfile] = [
    ComponentProfile(
        manufacturer="Diodes Incorporated",
        orderable_mpn="AP2112K-3.3",
        functional_class=FunctionalClass.REGULATOR_LDO,
        symbol_ref="Regulator_Linear:AP2112K-3.3",
        footprint_ref="Package_TO_SOT_SMD:SOT-23-5",
        pins=[
            Pin(number="1", name="VIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="2", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="EN", electrical_role=ElectricalRole.ENABLE, voltage_domain="5V"),
            Pin(number="4", name="NC", electrical_role=ElectricalRole.NO_CONNECT),
            Pin(number="5", name="VOUT", electrical_role=ElectricalRole.POWER_OUT, voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vin", operator="lte", value=6.5, unit="V"),
            Constraint(name="iout", operator="lte", value=0.6, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vin", operator="between", value=[3.5, 6.0], unit="V", notes="for 3.3V fixed output"),
            Constraint(name="iout", operator="lte", value=0.6, unit="A"),
            Constraint(name="ambient_temp", operator="between", value=[-40, 85], unit="C"),
        ],
        supply_domains=["5V", "3V3", "GND"],
        required_support_components=["input_cap_1uF", "output_cap_1uF"],
        recommended_support_components=["en_tie_to_vin"],
        boot_reset_config=["EN high enables output; float/low disables"],
        interface_characteristics={
            "dropout": "~250 mV typical at 600 mA",
            "output": "fixed 3.3 V ±1.5%",
        },
        approved_reference_circuits=["diodes:ap2112_typical_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:ap2112",
                kind="datasheet",
                title="AP2112 600mA CMOS LDO Regulator",
                uri="https://www.diodes.com/assets/Datasheets/AP2112.pdf",
                page=1,
                confidence=0.85,
            ),
            EvidenceRef(
                id="fixture:ldo_rail",
                kind="fixture",
                title="Golden LDO rail uses AP2112K-3.3",
                confidence=1.0,
            ),
        ],
    ),
    ComponentProfile(
        manufacturer="Advanced Monolithic Systems",
        orderable_mpn="AMS1117-3.3",
        functional_class=FunctionalClass.REGULATOR_LDO,
        symbol_ref="Regulator_Linear:AMS1117-3.3",
        footprint_ref="Package_TO_SOT_SMD:SOT-223-3_TabPin2",
        pins=[
            Pin(number="1", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="2", name="VOUT", electrical_role=ElectricalRole.POWER_OUT, voltage_domain="3V3"),
            Pin(number="3", name="VIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="5V"),
            Pin(number="4", name="TAB", electrical_role=ElectricalRole.POWER_OUT, voltage_domain="3V3"),
        ],
        absolute_maximum=[
            Constraint(name="vin", operator="lte", value=15, unit="V"),
            Constraint(name="iout", operator="lte", value=1.0, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vin", operator="between", value=[4.75, 12], unit="V"),
            Constraint(name="iout", operator="lte", value=0.8, unit="A", notes="thermal-limited in SOT-223"),
        ],
        supply_domains=["5V", "3V3", "GND"],
        required_support_components=["input_cap_10uF", "output_cap_22uF_tantalum_or_low_esr"],
        recommended_support_components=["thermal_pad_copper"],
        boot_reset_config=[],
        interface_characteristics={
            "dropout": "~1.1 V typical",
            "output": "fixed 3.3 V",
        },
        approved_reference_circuits=["ams:ams1117_typical"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:ams1117-3.3",
                kind="datasheet",
                title="AMS1117 1A LDO",
                uri="https://www.advanced-monolithic.com/pdf/ds1117.pdf",
                page=1,
                confidence=0.75,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Texas Instruments",
        orderable_mpn="TPS62130",
        functional_class=FunctionalClass.REGULATOR_BUCK,
        symbol_ref="Regulator_Switching:TPS62130",
        footprint_ref="Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm",
        pins=[
            Pin(number="1", name="AVIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="2", name="AGND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="3", name="FB", electrical_role=ElectricalRole.ANALOG_IN, interface_role="feedback", voltage_domain="VOUT"),
            Pin(number="4", name="FSW", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="freq_select", voltage_domain="VIN"),
            Pin(number="5", name="DEF", electrical_role=ElectricalRole.DIGITAL_IN, interface_role="def_select", voltage_domain="VIN"),
            Pin(number="6", name="SS/TR", electrical_role=ElectricalRole.ANALOG_IN, interface_role="soft_start", voltage_domain="VOUT"),
            Pin(number="7", name="SW", electrical_role=ElectricalRole.POWER_OUT, interface_role="switch_node", voltage_domain="VOUT"),
            Pin(number="8", name="PGND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="9", name="PVIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="10", name="EN", electrical_role=ElectricalRole.ENABLE, voltage_domain="VIN"),
            Pin(number="11", name="VOS", electrical_role=ElectricalRole.ANALOG_IN, interface_role="output_sense", voltage_domain="VOUT"),
            Pin(number="12", name="PG", electrical_role=ElectricalRole.OPEN_DRAIN, interface_role="power_good", voltage_domain="VOUT"),
            Pin(number="13", name="PVIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="14", name="SW", electrical_role=ElectricalRole.POWER_OUT, interface_role="switch_node", voltage_domain="VOUT"),
            Pin(number="15", name="SW", electrical_role=ElectricalRole.POWER_OUT, interface_role="switch_node", voltage_domain="VOUT"),
            Pin(number="16", name="PVIN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="17", name="EP", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
        ],
        absolute_maximum=[
            Constraint(name="vin", operator="lte", value=20, unit="V"),
            Constraint(name="iout", operator="lte", value=3.0, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vin", operator="between", value=[3.0, 17], unit="V"),
            Constraint(name="vout", operator="between", value=[0.9, 6.0], unit="V"),
            Constraint(name="iout", operator="lte", value=3.0, unit="A"),
        ],
        supply_domains=["VIN", "VOUT", "GND"],
        required_support_components=[
            "input_cap_10uF",
            "output_cap_22uF",
            "inductor_1uH_to_2u2H",
            "feedback_divider_rfb1_rfb2",
            "ss_cap_3n3",
        ],
        recommended_support_components=["pg_pullup_100k", "en_resistor_divider_uvlo"],
        boot_reset_config=["EN high enables converter; SS/TR sets soft-start ramp"],
        interface_characteristics={
            "topology": "synchronous buck DCS-Control",
            "switching_freq": "2.5 MHz typical (FSW=high)",
        },
        approved_reference_circuits=["ti:tps62130_evm"],
        simulation_model_refs=["ti:tps62130_pspice"],
        evidence_refs=[
            EvidenceRef(
                id="ds:tps62130",
                kind="datasheet",
                title="TPS6213x 3-V to 17-V 3-A Step-Down Converter",
                uri="https://www.ti.com/lit/ds/symlink/tps62130.pdf",
                page=1,
                confidence=0.85,
            )
        ],
    ),
    ComponentProfile(
        manufacturer="Monolithic Power Systems",
        orderable_mpn="MP1584EN",
        functional_class=FunctionalClass.REGULATOR_BUCK,
        symbol_ref="Regulator_Switching:MP1584EN",
        footprint_ref="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        pins=[
            Pin(number="1", name="BS", electrical_role=ElectricalRole.PASSIVE, interface_role="bootstrap"),
            Pin(number="2", name="IN", electrical_role=ElectricalRole.POWER_IN, voltage_domain="VIN"),
            Pin(number="3", name="SW", electrical_role=ElectricalRole.POWER_OUT, interface_role="switch_node", voltage_domain="VOUT"),
            Pin(number="4", name="GND", electrical_role=ElectricalRole.GROUND, voltage_domain="GND"),
            Pin(number="5", name="FB", electrical_role=ElectricalRole.ANALOG_IN, interface_role="feedback", voltage_domain="VOUT"),
            Pin(number="6", name="COMP", electrical_role=ElectricalRole.ANALOG_OUT, interface_role="compensation"),
            Pin(number="7", name="EN", electrical_role=ElectricalRole.ENABLE, voltage_domain="VIN"),
            Pin(number="8", name="NC", electrical_role=ElectricalRole.NO_CONNECT),
        ],
        absolute_maximum=[
            Constraint(name="vin", operator="lte", value=28, unit="V"),
            Constraint(name="iout", operator="lte", value=3.0, unit="A"),
        ],
        recommended_operating=[
            Constraint(name="vin", operator="between", value=[4.5, 28], unit="V"),
            Constraint(name="vout", operator="between", value=[0.8, 20], unit="V"),
        ],
        supply_domains=["VIN", "VOUT", "GND"],
        required_support_components=[
            "input_cap_10uF",
            "output_cap_22uF",
            "inductor_4u7_to_22uH",
            "bootstrap_cap_10nF",
            "feedback_divider",
            "comp_rc_network",
        ],
        recommended_support_components=["en_pullup_or_divider"],
        boot_reset_config=["EN > 1.5 V enables; pull low to shut down"],
        interface_characteristics={
            "topology": "asynchronous buck",
            "switching_freq": "1.5 MHz typical",
        },
        approved_reference_circuits=["mps:mp1584_typical_app"],
        simulation_model_refs=[],
        evidence_refs=[
            EvidenceRef(
                id="ds:mp1584en",
                kind="datasheet",
                title="MP1584 3A 1.5MHz 28V Step-Down Converter",
                uri="https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP1584/",
                page=1,
                confidence=0.75,
            )
        ],
    ),
]
