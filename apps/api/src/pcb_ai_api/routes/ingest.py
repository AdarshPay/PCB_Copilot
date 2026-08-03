"""Ingest a KiCad schematic, normalize to Circuit IR, optionally run rules."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from pcb_ai_circuit_ir.models import Design, Finding, ReviewReport
from pcb_ai_kicad_adapter import ingest_schematic
from pcb_ai_verification import run_rules

router = APIRouter(tags=["ingest"])


class IngestResponse(BaseModel):
    design: Design
    findings: list[Finding] = Field(default_factory=list)
    report: ReviewReport | None = None


@router.post("/ingest/schematic", response_model=IngestResponse)
async def ingest_schematic_endpoint(
    file: UploadFile = File(..., description="KiCad .kicad_sch upload"),
    design_id: str | None = Form(default=None),
    run_verification: bool = Form(default=True),
) -> IngestResponse:
    raw = await file.read()
    text = raw.decode("utf-8")
    stem = (file.filename or "upload").removesuffix(".kicad_sch")
    design = ingest_schematic(text, design_id=design_id or f"kicad.{stem}")
    findings: list[Finding] = []
    report: ReviewReport | None = None
    if run_verification:
        findings = run_rules(design)
        report = ReviewReport(
            design_id=design.id,
            design_revision=design.revision,
            findings=findings,
            metadata={"rule_pack": "v0", "source": "kicad_ingest", "filename": file.filename},
        )
    return IngestResponse(design=design, findings=findings, report=report)
