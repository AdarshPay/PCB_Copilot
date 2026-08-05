"""Propose remediations and apply them on an IR copy (temp-branch style).

Guardrails: never writes production CAD. Planner stays opt-in via
``ProposeRequest.enabled`` (default False). Apply runs only on a deep-copied
Design returned alongside the proposal.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pcb_ai_agent import Planner, PlannerDisabled
from pcb_ai_circuit_ir.models import Design, Finding, Operation
from pcb_ai_transactions import apply_operations, export_branch_diff
from pcb_ai_verification import run_rules

router = APIRouter(tags=["proposals"])


class ProposeRequest(BaseModel):
    design: Design
    findings: list[Finding] | None = None
    enabled: bool = False
    apply_on_copy: bool = True


class ProposeResponse(BaseModel):
    operations: list[Operation] = Field(default_factory=list)
    after_design: Design | None = None
    branch_diff: dict | None = None
    finding_count: int = 0


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

    return ProposeResponse(
        operations=operations,
        after_design=after,
        branch_diff=branch_diff,
        finding_count=len(findings),
    )
