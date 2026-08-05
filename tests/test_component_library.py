"""Component library profile and registry tests."""

from __future__ import annotations

import pytest
from pcb_ai_circuit_ir.models import FunctionalClass
from pcb_ai_component_library import ComponentProfile, get_by_mpn, list_by_class, load_all

# Golden-fixture MPNs that curated profiles must cover.
FIXTURE_MPNS = {"RP2040", "TMP117", "AP2112K-3.3", "CP2102"}

MIN_PROFILE_COUNT = 12


def test_load_all_returns_curated_batch() -> None:
    profiles = load_all()
    assert len(profiles) >= MIN_PROFILE_COUNT
    assert all(isinstance(p, ComponentProfile) for p in profiles)


def test_mpns_are_unique() -> None:
    mpns = [p.orderable_mpn for p in load_all()]
    assert len(mpns) == len(set(mpns))


def test_profiles_have_required_content() -> None:
    for profile in load_all():
        assert profile.manufacturer.strip()
        assert profile.orderable_mpn.strip()
        assert profile.symbol_ref.strip()
        assert profile.footprint_ref.strip()
        assert len(profile.pins) >= 2
        assert profile.supply_domains, f"{profile.orderable_mpn} missing supply_domains"
        assert profile.evidence_refs, f"{profile.orderable_mpn} missing evidence_refs"
        pin_numbers = [pin.number for pin in profile.pins]
        assert all(n.strip() for n in pin_numbers)
        assert all(pin.name.strip() for pin in profile.pins)


def test_get_by_mpn_known_and_unknown() -> None:
    rp = get_by_mpn("RP2040")
    assert rp is not None
    assert rp.functional_class == FunctionalClass.MCU
    assert get_by_mpn("rp2040") is rp  # case-insensitive
    assert get_by_mpn("NOT-A-REAL-MPN") is None


def test_fixture_mpns_are_present() -> None:
    for mpn in FIXTURE_MPNS:
        profile = get_by_mpn(mpn)
        assert profile is not None, f"missing fixture MPN profile: {mpn}"


def test_list_by_class_filters() -> None:
    mcus = list_by_class(FunctionalClass.MCU)
    assert {p.orderable_mpn for p in mcus} >= {"RP2040", "STM32F103C8T6"}
    sensors = list_by_class("sensor")
    assert {p.orderable_mpn for p in sensors} >= {"TMP117", "BME280", "ICM-20602"}
    assert list_by_class(FunctionalClass.PROGRAMMING) == []


def test_list_by_class_rejects_unknown_string() -> None:
    with pytest.raises(ValueError):
        list_by_class("not_a_class")


def test_support_components_present_where_expected() -> None:
    tmp = get_by_mpn("TMP117")
    assert tmp is not None
    assert any("pullup" in s for s in tmp.required_support_components)

    ldo = get_by_mpn("AP2112K-3.3")
    assert ldo is not None
    assert any("cap" in s for s in ldo.required_support_components)

    mcu = get_by_mpn("RP2040")
    assert mcu is not None
    assert mcu.boot_reset_config


def test_family_coverage() -> None:
    classes = {p.functional_class for p in load_all()}
    assert classes >= {
        FunctionalClass.MCU,
        FunctionalClass.SENSOR,
        FunctionalClass.REGULATOR_LDO,
        FunctionalClass.REGULATOR_BUCK,
        FunctionalClass.TRANSCEIVER,
        FunctionalClass.INTERFACE_BRIDGE,
        FunctionalClass.PROTECTION,
    }
