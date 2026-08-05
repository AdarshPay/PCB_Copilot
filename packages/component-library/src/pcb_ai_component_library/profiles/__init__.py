"""Curated profile catalog — first batch toward the 20–30 part target."""

from __future__ import annotations

from pcb_ai_component_library.models import ComponentProfile
from pcb_ai_component_library.profiles.bridges import PROFILES as BRIDGE_PROFILES
from pcb_ai_component_library.profiles.mcu import PROFILES as MCU_PROFILES
from pcb_ai_component_library.profiles.protection import PROFILES as PROTECTION_PROFILES
from pcb_ai_component_library.profiles.regulators import PROFILES as REGULATOR_PROFILES
from pcb_ai_component_library.profiles.sensors import PROFILES as SENSOR_PROFILES
from pcb_ai_component_library.profiles.transceivers import PROFILES as TRANSCEIVER_PROFILES

ALL_PROFILES: list[ComponentProfile] = [
    *MCU_PROFILES,
    *SENSOR_PROFILES,
    *REGULATOR_PROFILES,
    *TRANSCEIVER_PROFILES,
    *BRIDGE_PROFILES,
    *PROTECTION_PROFILES,
]

__all__ = ["ALL_PROFILES"]
