"""Review endpoints: submit a Circuit IR design and receive findings."""

from __future__ import annotations

from fastapi import APIRouter

from pcb_ai_circuit_ir.models import Design, ReviewReport
from pcb_ai_verification import run_rules

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewReport)
def create_review(design: Design) -> ReviewReport:
    findings = run_rules(design)
    return ReviewReport(
        design_id=design.id,
        design_revision=design.revision,
        findings=findings,
        metadata={"rule_pack": "v0", "source": "deterministic"},
    )
