"""ERC report normalization and offline runner tests."""

from __future__ import annotations

import pytest

from pcb_ai_kicad_adapter import ingest_schematic
from pcb_ai_verification import (
    attach_design_objects,
    normalize_erc_text,
    parse_erc_report,
    run_schematic_erc,
)
from pcb_ai_worker.main import process_job
from tests.conftest import KICAD_FIXTURES

ERC_JSON = KICAD_FIXTURES / "rc_divider_erc.json"
RC_SCH = KICAD_FIXTURES / "rc_divider.kicad_sch"


def test_parse_erc_json_fixture() -> None:
    findings = parse_erc_report(ERC_JSON)
    assert len(findings) == 3
    by_rule = {f.rule_id: f for f in findings}
    assert "erc.pin_not_connected" in by_rule
    assert "erc.label_dangling" in by_rule
    assert "erc.pin_to_pin" in by_rule
    pin = by_rule["erc.pin_not_connected"]
    assert pin.severity.value == "error"
    assert pin.source == "kicad_erc"
    assert pin.evidence_refs and pin.evidence_refs[0].kind == "erc"
    assert "R1" in pin.objects
    assert "R1.1" in pin.objects
    assert "00000000-0000-4000-8000-000000000011" in pin.objects


def test_erc_maps_to_schematic_uuids() -> None:
    design = ingest_schematic(RC_SCH)
    findings = parse_erc_report(ERC_JSON, design=design)
    pin_to_pin = next(f for f in findings if f.rule_id == "erc.pin_to_pin")
    # Component instance UUIDs from the schematic + references.
    assert "00000000-0000-4000-8000-000000000001" in pin_to_pin.objects
    assert "00000000-0000-4000-8000-000000000002" in pin_to_pin.objects
    assert "R1" in pin_to_pin.objects
    assert "R2" in pin_to_pin.objects


def test_attach_design_objects_roundtrip() -> None:
    design = ingest_schematic(RC_SCH)
    raw = parse_erc_report(ERC_JSON)
    remapped = attach_design_objects(raw, design)
    assert any("R1" in f.objects for f in remapped)


def test_normalize_erc_text_report() -> None:
    text = """\
ERC report (2026-08-02), rc_divider.kicad_sch
***** Sheet /
[pin_not_connected]: Pin not connected
    ; R1 Pin 1 [~, Passive, Line]
[label_dangling]: Label not connected to anything
    @ (76.2 mm, 63.5 mm): Local label MID
"""
    findings = normalize_erc_text(text)
    assert len(findings) == 2
    assert findings[0].rule_id == "erc.pin_not_connected"
    assert "R1" in findings[0].objects
    assert findings[1].rule_id == "erc.label_dangling"


def test_run_schematic_erc_offline_report() -> None:
    design = ingest_schematic(RC_SCH)
    result = run_schematic_erc(report_path=ERC_JSON, design=design)
    assert result.mode == "report"
    assert len(result.findings) == 3


def test_run_schematic_erc_mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PCB_AI_ERC_MODE", "mock")
    monkeypatch.setenv("PCB_AI_ERC_MOCK_REPORT", str(ERC_JSON))
    result = run_schematic_erc(mode="mock")
    assert result.mode == "mock"
    assert result.findings


def test_worker_run_erc_from_report_path() -> None:
    result = process_job(
        {
            "type": "run_erc",
            "report_path": str(ERC_JSON),
        }
    )
    assert result["type"] == "run_erc"
    assert result["status"] == "ok"
    assert result["finding_count"] == 3
    assert any(f["rule_id"] == "erc.pin_not_connected" for f in result["findings"])


def test_worker_run_erc_from_inline_report() -> None:
    import json

    payload = json.loads(ERC_JSON.read_text(encoding="utf-8"))
    result = process_job({"type": "run_erc", "erc_report": payload})
    assert result["finding_count"] == 3


def test_worker_run_erc_with_schematic_ingest() -> None:
    """Worker can attach Design from schematic_path when only a report is given."""
    result = process_job(
        {
            "type": "run_erc",
            "schematic_path": str(RC_SCH),
            "report_path": str(ERC_JSON),
        }
    )
    assert result["status"] == "ok"
    pin = next(f for f in result["findings"] if f["rule_id"] == "erc.pin_to_pin")
    assert "R1" in pin["objects"]
    assert "R2" in pin["objects"]
