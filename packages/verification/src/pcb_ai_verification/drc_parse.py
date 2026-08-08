"""Parse KiCad DRC reports into Finding objects (Phase B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pcb_ai_circuit_ir.models import EvidenceRef, Finding, Severity

_SEVERITY_MAP: dict[str, Severity] = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
    "exclusion": Severity.INFO,
    "excluded": Severity.INFO,
}


def parse_drc_report(
    source: str | Path | dict[str, Any],
) -> list[Finding]:
    """Parse DRC JSON dict/file or a minimal fixture schema."""
    if isinstance(source, dict):
        return normalize_drc_json(source)

    path: Path | None = None
    if isinstance(source, Path):
        path = source
        text = source.read_text(encoding="utf-8")
    else:
        text = source
        candidate = Path(source)
        if "\n" not in source and candidate.is_file():
            path = candidate
            text = candidate.read_text(encoding="utf-8")

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("DRC JSON root must be an object")
    return normalize_drc_json(data, source_name=path.name if path else None)


def normalize_drc_json(
    report: dict[str, Any],
    *,
    source_name: str | None = None,
) -> list[Finding]:
    """Convert KiCad-like DRC JSON (or our fixture schema) into Findings."""
    findings: list[Finding] = []
    violations = report.get("violations") or []
    # KiCad sometimes nests under sheets/violations — also accept flat list.
    if not violations and "sheets" in report:
        for sheet in report.get("sheets") or []:
            violations.extend(sheet.get("violations") or [])

    for viol in violations:
        vtype = str(viol.get("type") or viol.get("severity_type") or "drc")
        severity_raw = str(viol.get("severity") or "error").lower()
        severity = _SEVERITY_MAP.get(severity_raw, Severity.ERROR)
        desc = str(viol.get("description") or viol.get("message") or vtype)
        objects: list[str] = []
        for item in viol.get("items") or []:
            if isinstance(item, dict):
                for key in ("description", "pos", "uuid"):
                    if item.get(key):
                        objects.append(str(item[key]))
                        break
            elif isinstance(item, str):
                objects.append(item)
        findings.append(
            Finding(
                rule_id=f"drc.{vtype}",
                severity=severity,
                objects=objects,
                explanation=desc,
                evidence_refs=[
                    EvidenceRef(
                        id=f"drc:{vtype}",
                        kind="drc",
                        title=vtype,
                        uri=source_name,
                    )
                ],
                source="kicad_drc",
            )
        )
    return findings
