"""API smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pcb_ai_api.main import app
from tests.conftest import load_golden

client = TestClient(app)


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
