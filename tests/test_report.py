"""Semantic review report and HTML artifact tests."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Operation
from pcb_ai_transactions import apply_operations
from pcb_ai_verification import build_review_report, render_html_report
from tests.conftest import load_golden
from tests.mutation.ir_mutators import mutate_output_conflict


def test_build_review_report_includes_summary_and_fragments() -> None:
    design = mutate_output_conflict(load_golden("rc_divider.json"))
    report = build_review_report(design)
    assert report.design_id == design.id
    assert report.summary["finding_count"] >= 1
    assert any(f.rule_id == "elec.output_conflict" for f in report.findings)
    assert report.net_fragments
    assert all(frag.phase == "current" for frag in report.net_fragments)
    assert any(frag.related_finding_ids for frag in report.net_fragments)


def test_html_report_contains_findings_and_evidence() -> None:
    design = load_golden("output_conflict.json")
    report = build_review_report(design)
    html = render_html_report(report, design)
    assert "elec.output_conflict" in html
    assert "Evidence" in html
    assert "Net fragments" in html
    assert design.id in html or (design.name or "") in html


def test_before_after_net_fragments_with_operations() -> None:
    design = mutate_output_conflict(load_golden("rc_divider.json"))
    ops = [
        Operation(
            type="set_component_value",
            target="R1",
            payload={"value": "20k"},
            risk_tier="low",
            confidence=1.0,
        )
    ]
    after = apply_operations(design, ops)
    report = build_review_report(design, operations=ops, after_design=after)
    phases = {frag.phase for frag in report.net_fragments}
    assert "before" in phases
    assert "after" in phases
    assert report.metadata.get("semantic_diff") is None  # provided after_design skips auto-diff
    # When caller supplies after_design, semantic_diff is only added if we applied ops ourselves.
    report_auto = build_review_report(design, operations=ops)
    assert "semantic_diff" in report_auto.metadata
    assert report_auto.metadata["semantic_diff"]["changed_components"] == ["R1"]


def test_api_review_html() -> None:
    from fastapi.testclient import TestClient

    from pcb_ai_api.main import app

    client = TestClient(app)
    design = load_golden("output_conflict.json")
    response = client.post(
        "/v1/reviews/html",
        json=design.model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "elec.output_conflict" in response.text
