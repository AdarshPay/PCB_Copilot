"""Golden fixture validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcb_ai_circuit_ir.models import Design
from tests.conftest import FIXTURES, load_golden

GOLDEN_FILES = sorted(FIXTURES.glob("*.json"))


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_golden_fixtures_validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    design = Design.model_validate(data)
    assert design.id
    assert design.components
    dumped = design.model_dump(mode="json", by_alias=True)
    round_trip = Design.model_validate(dumped)
    assert round_trip.id == design.id


def test_three_golden_circuits_exist() -> None:
    names = {p.stem for p in GOLDEN_FILES}
    assert names >= {"rc_divider", "i2c_sensor", "output_conflict"}


def test_load_helper() -> None:
    design = load_golden("rc_divider.json")
    assert design.name == "RC voltage divider"
