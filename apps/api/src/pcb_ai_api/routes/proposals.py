"""Propose remediations and record engineer approve/reject decisions.

Guardrails: never writes production CAD. Planner stays opt-in via
``ProposeRequest.enabled`` (default False). Apply runs only on a deep-copied
Design returned alongside the proposal. Decision telemetry is offline-local
(in-memory or optional JSONL); no external analytics.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from pcb_ai_agent import (
    DecisionKind,
    DecisionRecord,
    DecisionTelemetry,
    Planner,
    PlannerDisabled,
    make_decision_store,
)
from pcb_ai_api.settings import settings
from pcb_ai_circuit_ir.models import Design, Finding, Operation
from pcb_ai_transactions import apply_operations, export_branch_diff
from pcb_ai_verification import run_rules

router = APIRouter(tags=["proposals"])

_telemetry = DecisionTelemetry(
    make_decision_store(settings.decision_telemetry_path or None)
)


def get_decision_telemetry() -> DecisionTelemetry:
    """Expose the process-local telemetry singleton (tests may replace store)."""
    return _telemetry


def reset_decision_telemetry(
    telemetry: DecisionTelemetry | None = None,
) -> DecisionTelemetry:
    """Replace the module singleton (used by tests)."""
    global _telemetry
    _telemetry = telemetry or DecisionTelemetry()
    return _telemetry


class ProposeRequest(BaseModel):
    design: Design
    findings: list[Finding] | None = None
    enabled: bool = False
    apply_on_copy: bool = True


class ProposeResponse(BaseModel):
    proposal_id: str
    operations: list[Operation] = Field(default_factory=list)
    after_design: Design | None = None
    branch_diff: dict | None = None
    finding_count: int = 0


class DecisionRequest(BaseModel):
    decision: DecisionKind
    reason: str | None = None
    design_id: str | None = None
    operation_ids: list[str] | None = None
    rule_ids: list[str] | None = None


class CreateDecisionRequest(DecisionRequest):
    proposal_id: str


def _rule_ids_for_proposal(
    findings: list[Finding], operations: list[Operation]
) -> list[str]:
    ids: set[str] = {f.rule_id for f in findings}
    for op in operations:
        ids.update(op.expected_checks)
    return sorted(ids)


@router.post("/proposals", response_model=ProposeResponse)
def create_proposal(body: ProposeRequest) -> ProposeResponse:
    findings = body.findings if body.findings is not None else run_rules(body.design)
    planner = Planner(enabled=body.enabled)
    try:
        operations = planner.propose(body.design, findings)
    except PlannerDisabled as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    after: Design | None = None
    branch_diff: dict | None = None
    if body.apply_on_copy and operations:
        after = apply_operations(body.design, operations)
        branch_diff = export_branch_diff(
            body.design, after, operations=operations, branch_name="temp"
        )

    snapshot = get_decision_telemetry().register_proposal(
        design_id=body.design.id,
        operation_ids=[op.id for op in operations],
        rule_ids=_rule_ids_for_proposal(findings, operations),
    )

    return ProposeResponse(
        proposal_id=snapshot.proposal_id,
        operations=operations,
        after_design=after,
        branch_diff=branch_diff,
        finding_count=len(findings),
    )


@router.post(
    "/proposals/{proposal_id}/decision",
    response_model=DecisionRecord,
)
def submit_proposal_decision(
    proposal_id: str, body: DecisionRequest
) -> DecisionRecord:
    return _record_decision(proposal_id=proposal_id, body=body)


@router.post("/decisions", response_model=DecisionRecord)
def create_decision(body: CreateDecisionRequest) -> DecisionRecord:
    return _record_decision(proposal_id=body.proposal_id, body=body)


@router.get("/decisions", response_model=list[DecisionRecord])
def list_decisions(limit: int = Query(default=50, ge=1, le=500)) -> list[DecisionRecord]:
    return get_decision_telemetry().list_recent(limit=limit)


def _record_decision(proposal_id: str, body: DecisionRequest) -> DecisionRecord:
    try:
        return get_decision_telemetry().record_decision(
            proposal_id=proposal_id,
            decision=body.decision,
            reason=body.reason,
            design_id=body.design_id,
            operation_ids=body.operation_ids,
            rule_ids=body.rule_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
