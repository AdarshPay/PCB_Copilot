"""JSON Schema export helpers for Circuit IR documents."""

from __future__ import annotations

import json
from pathlib import Path

from pcb_ai_circuit_ir.models import Design, EvidenceRef, Finding, Operation, ReviewReport


def export_schemas(output_dir: Path | str) -> dict[str, Path]:
    """Write JSON Schema documents for the core public types."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    targets = {
        "circuit-ir.schema.json": Design,
        "finding.schema.json": Finding,
        "transaction.schema.json": Operation,
        "evidence.schema.json": EvidenceRef,
        "review-report.schema.json": ReviewReport,
    }
    written: dict[str, Path] = {}
    for filename, model in targets.items():
        path = out / filename
        schema = model.model_json_schema()
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        written[filename] = path
    return written
