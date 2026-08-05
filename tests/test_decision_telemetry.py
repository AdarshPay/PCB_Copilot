"""Engineer approval/rejection telemetry tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pcb_ai_agent import (
    DecisionKind,
    DecisionTelemetry,
    InMemoryDecisionStore,
    JsonlDecisionStore,
)
from pcb_ai_api.main import app
from pcb_ai_api.routes import proposals as proposals_route
from tests.conftest import load_golden
from tests.mutation.ir_mutators import mutate_missing_open_drain_pullup

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_telemetry() -> None:
    """Isolate API decision store between tests."""
    proposals_route.reset_decision_telemetry(DecisionTelemetry(InMemoryDecisionStore()))
    yield
    proposals_route.reset_decision_telemetry(DecisionTelemetry(InMemoryDecisionStore()))


def test_inmemory_approve_and_reject() -> None:
    tel = DecisionTelemetry(InMemoryDecisionStore())
    snap = tel.register_proposal(
        design_id="design.a",
        operation_ids=["op-1", "op-2"],
        rule_ids=["elec.open_drain_pullup"],
    )

    approved = tel.record_decision(
        proposal_id=snap.proposal_id,
        decision=DecisionKind.APPROVE,
        reason="looks correct",
    )
    assert approved.decision is DecisionKind.APPROVE
    assert approved.design_id == "design.a"
    assert approved.operation_ids == ["op-1", "op-2"]
    assert approved.rule_ids == ["elec.open_drain_pullup"]
    assert approved.reason == "looks correct"
    assert approved.timestamp.tzinfo is not None

    rejected = tel.record_decision(
        proposal_id=snap.proposal_id,
        decision="reject",
        reason="wrong pull-up value",
    )
    assert rejected.decision is DecisionKind.REJECT
    assert rejected.reason == "wrong pull-up value"

    recent = tel.list_recent(limit=10)
    assert len(recent) == 2
    assert {r.decision for r in recent} == {DecisionKind.APPROVE, DecisionKind.REJECT}
    assert tel.list_for_proposal(snap.proposal_id) == recent


def test_jsonl_store_persists(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    store = JsonlDecisionStore(path)
    tel = DecisionTelemetry(store)
    snap = tel.register_proposal(design_id="d1", operation_ids=["o1"], rule_ids=["r1"])
    tel.record_decision(proposal_id=snap.proposal_id, decision="approve")

    reloaded = DecisionTelemetry(JsonlDecisionStore(path))
    rows = reloaded.list_recent()
    assert len(rows) == 1
    assert rows[0].decision is DecisionKind.APPROVE
    assert rows[0].design_id == "d1"
    assert path.exists()
    assert "approve" in path.read_text(encoding="utf-8")


def test_record_without_registered_proposal_requires_design_id() -> None:
    tel = DecisionTelemetry()
    with pytest.raises(ValueError, match="design_id required"):
        tel.record_decision(proposal_id="missing", decision="approve")

    record = tel.record_decision(
        proposal_id="missing",
        decision="reject",
        design_id="design.orphan",
        operation_ids=["op-x"],
        rule_ids=["struct.footprint_presence"],
    )
    assert record.design_id == "design.orphan"
    assert record.operation_ids == ["op-x"]


def test_api_propose_then_approve_and_reject() -> None:
    design = mutate_missing_open_drain_pullup(load_golden("i2c_sensor.json"))
    propose = client.post(
        "/v1/proposals",
        json={
            "design": design.model_dump(mode="json", by_alias=True),
            "enabled": True,
            "apply_on_copy": True,
        },
    )
    assert propose.status_code == 200
    body = propose.json()
    proposal_id = body["proposal_id"]
    assert proposal_id
    assert body["operations"]

    approve = client.post(
        f"/v1/proposals/{proposal_id}/decision",
        json={"decision": "approve", "reason": "ship it"},
    )
    assert approve.status_code == 200
    approved = approve.json()
    assert approved["proposal_id"] == proposal_id
    assert approved["decision"] == "approve"
    assert approved["design_id"] == design.id
    assert approved["reason"] == "ship it"
    assert approved["operation_ids"]
    assert "elec.open_drain_pullup" in approved["rule_ids"]

    reject = client.post(
        "/v1/decisions",
        json={
            "proposal_id": proposal_id,
            "decision": "reject",
            "reason": "prefer different value",
        },
    )
    assert reject.status_code == 200
    assert reject.json()["decision"] == "reject"

    listed = client.get("/v1/decisions", params={"limit": 10})
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 2
    assert rows[0]["decision"] == "approve"
    assert rows[1]["decision"] == "reject"


def test_api_decision_unknown_proposal_without_design_id_is_400() -> None:
    response = client.post(
        "/v1/proposals/does-not-exist/decision",
        json={"decision": "approve"},
    )
    assert response.status_code == 400
    assert "design_id" in response.json()["detail"]
