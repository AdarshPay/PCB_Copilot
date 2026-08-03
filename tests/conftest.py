"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pcb_ai_circuit_ir.models import Design

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "golden"
KICAD_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kicad"


def load_golden(name: str) -> Design:
    path = FIXTURES / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return Design.model_validate(data)
