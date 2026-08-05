"""Review endpoints: submit a Circuit IR design and receive findings / HTML report."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pcb_ai_circuit_ir.models import Design, ReviewReport
from pcb_ai_verification import build_review_report, render_html_report

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewReport)
def create_review(design: Design) -> ReviewReport:
    return build_review_report(design)


@router.post("/reviews/html", response_class=HTMLResponse)
def create_review_html(design: Design) -> HTMLResponse:
    report = build_review_report(design)
    return HTMLResponse(content=render_html_report(report, design))
