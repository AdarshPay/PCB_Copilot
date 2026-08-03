"""API smoke tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from pcb_ai_api.main import app
from tests.conftest import load_golden

client = TestClient(app)

RC_DIVIDER = Path(__file__).resolve().parent / "fixtures" / "kicad" / "rc_divider.kicad_sch"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_review_output_conflict() -> None:
    design = load_golden("output_conflict.json")
    response = client.post("/v1/reviews", json=design.model_dump(mode="json", by_alias=True))
    assert response.status_code == 200
    body = response.json()
    assert body["design_id"] == design.id
    assert any(f["rule_id"] == "elec.output_conflict" for f in body["findings"])


def test_ingest_schematic() -> None:
    content = RC_DIVIDER.read_bytes()
    response = client.post(
        "/v1/ingest/schematic",
        files={"file": ("rc_divider.kicad_sch", content, "application/octet-stream")},
        data={"run_verification": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["design"]["id"] == "kicad.rc_divider"
    refs = {c["reference"] for c in body["design"]["components"]}
    assert {"R1", "R2"} <= refs
    assert body["report"] is not None
