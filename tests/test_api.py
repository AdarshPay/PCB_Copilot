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
    assert body["summary"]["finding_count"] >= 1
    assert body["net_fragments"]


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


def test_propose_disabled_returns_403() -> None:
    design = load_golden("output_conflict.json")
    response = client.post(
        "/v1/proposals",
        json={"design": design.model_dump(mode="json", by_alias=True), "enabled": False},
    )
    assert response.status_code == 403


def test_propose_apply_on_copy() -> None:
    from tests.mutation.ir_mutators import mutate_missing_open_drain_pullup

    design = mutate_missing_open_drain_pullup(load_golden("i2c_sensor.json"))
    response = client.post(
        "/v1/proposals",
        json={
            "design": design.model_dump(mode="json", by_alias=True),
            "enabled": True,
            "apply_on_copy": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposal_id"]
    assert body["operations"]
    assert body["after_design"] is not None
    assert body["branch_diff"]["production_mutation"] is False
    assert any(op["type"] == "add_component" for op in body["operations"])


def test_temp_branch_endpoint_emits_schematic() -> None:
    import json

    content = RC_DIVIDER.read_bytes()
    ops = [
        {
            "type": "set_component_value",
            "target": "R2",
            "payload": {"value": "4.7k"},
            "risk_tier": "low",
            "confidence": 1.0,
        }
    ]
    response = client.post(
        "/v1/temp-branch",
        files={"file": ("rc_divider.kicad_sch", content, "application/octet-stream")},
        data={"operations_json": json.dumps(ops), "branch_name": "api-temp"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["production_mutation"] is False
    assert body["human_approval_required"] is True
    assert body["schematic_text"].startswith("(kicad_sch")
    assert body["branch_diff"]["production_mutation"] is False
    assert body["temp_schematic_name"] == "rc_divider.kicad_sch"
    # Production fixture on disk must remain untouched by the API path.
    assert RC_DIVIDER.read_bytes() == content


def test_layout_endpoint_from_schematic() -> None:
    content = RC_DIVIDER.read_bytes()
    response = client.post(
        "/v1/layout",
        files={"file": ("rc_divider.kicad_sch", content, "application/octet-stream")},
        data={"pcb_name": "api-layout.kicad_pcb", "register_proposal": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["production_mutation"] is False
    assert body["human_approval_required"] is True
    assert body["proposal_id"]
    assert body["job_id"] == body["proposal_id"]
    assert body["pcb_text"].startswith("(kicad_pcb")
    assert body["metadata"]["placed"] >= 1
    assert body["operations"]
    # Production fixture on disk must remain untouched.
    assert RC_DIVIDER.read_bytes() == content


def test_layout_from_design_json() -> None:
    design = load_golden("rc_divider.json")
    response = client.post(
        "/v1/layout/from-design",
        json={
            "design": design.model_dump(mode="json", by_alias=True),
            "pcb_name": "golden-layout.kicad_pcb",
            "register_proposal": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["design_id"] == design.id
    assert body["metadata"]["placed"] == len(design.components)
    assert body["pcb_text"].startswith("(kicad_pcb")
    assert body["production_mutation"] is False


def test_temp_board_from_design() -> None:
    design = load_golden("rc_divider.json")
    response = client.post(
        "/v1/temp-board/from-design",
        json={
            "design": design.model_dump(mode="json", by_alias=True),
            "pcb_name": "rc-copilot.kicad_pcb",
            "register_proposal": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposal_id"]
    assert body["temp_board_name"] == "rc-copilot.kicad_pcb"
    assert body["pcb_text"].startswith("(kicad_pcb")
    assert body["production_mutation"] is False
    assert body["human_approval_required"] is True
    assert body["branch_diff"]["production_mutation"] is False
    assert body["branch_diff"]["placed_after"] == len(design.components)
    # Layout proposal must land in decision telemetry for approve/reject.
    approve = client.post(
        f"/v1/proposals/{body['proposal_id']}/decision",
        json={"decision": "approve", "reason": "temp board ok"},
    )
    assert approve.status_code == 200
    assert approve.json()["proposal_id"] == body["proposal_id"]
    assert approve.json()["design_id"] == design.id


def test_temp_board_from_schematic() -> None:
    content = RC_DIVIDER.read_bytes()
    response = client.post(
        "/v1/temp-board",
        files={"file": ("rc_divider.kicad_sch", content, "application/octet-stream")},
        data={"pcb_name": "api-temp-board.kicad_pcb", "register_proposal": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposal_id"]
    assert body["temp_board_name"] == "api-temp-board.kicad_pcb"
    assert body["pcb_text"].startswith("(kicad_pcb")
    assert body["production_mutation"] is False
    assert body["human_approval_required"] is True
    assert RC_DIVIDER.read_bytes() == content


def test_temp_board_refuses_are_covered_by_compiler(tmp_path) -> None:
    from pcb_ai_transactions import TransactionError, compile_temp_board_branch

    design = load_golden("rc_divider.json")
    source = tmp_path / "prod.kicad_pcb"
    source.write_text("(kicad_pcb (version 20240108) (generator pcb_ai))\n", encoding="utf-8")
    try:
        compile_temp_board_branch(
            design,
            tmp_path,
            pcb_name="prod.kicad_pcb",
            source_pcb=source,
            register_proposal=False,
        )
    except TransactionError:
        return
    raise AssertionError("expected TransactionError when overwriting production path")
