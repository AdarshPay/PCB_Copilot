"""Parse KiCad ERC reports into normalized Finding objects.

Supports the KiCad 9+/10 JSON schema (``https://schemas.kicad.org/erc.v1.json``)
with violations nested under ``sheets[].violations``, plus a small text-report
fallback for classic ``.rpt`` output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pcb_ai_circuit_ir.models import EvidenceRef, Finding, Severity

from pcb_ai_verification.erc_map import collect_objects_from_items

_SEVERITY_MAP: dict[str, Severity] = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
    "exclusion": Severity.INFO,
    "excluded": Severity.INFO,
    "action": Severity.INFO,
    "ignore": Severity.INFO,
}

# Classic text report: "[pin_not_connected]: Pin not connected"
_TEXT_VIOLATION = re.compile(
    r"^\[(?P<type>[^\]]+)\]:\s*(?P<desc>.+)$"
)
# Alternate: "ErrType(3): description"
_TEXT_ERRTYPE = re.compile(
    r"^ErrType\(\d+\):\s*(?P<desc>.+)$"
)
_TEXT_ITEM = re.compile(
    r"^\s*(?:;|@)\s*(?:\([^)]*\)\s*)?:?\s*(?P<body>.+)$"
)


def parse_erc_report(
    source: str | Path | dict[str, Any],
    *,
    design: Any | None = None,
) -> list[Finding]:
    """Parse an ERC JSON dict, JSON file, JSON text, or classic ``.rpt`` text."""
    if isinstance(source, dict):
        return normalize_erc_json(source, design=design)

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

    stripped = text.lstrip()
    if stripped.startswith("{") or (path is not None and path.suffix.lower() == ".json"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("ERC JSON root must be an object")
        return normalize_erc_json(data, design=design)

    return normalize_erc_text(text, design=design, source_name=path.name if path else None)


def normalize_erc_json(
    report: dict[str, Any],
    *,
    design: Any | None = None,
) -> list[Finding]:
    """Convert a KiCad ERC JSON report into Finding objects."""
    kicad_version = str(report.get("kicad_version") or "")
    report_source = str(report.get("source") or "")
    findings: list[Finding] = []

    for sheet_path, violation in _iter_violations(report):
        findings.append(
            _violation_to_finding(
                violation,
                sheet_path=sheet_path,
                report_source=report_source,
                kicad_version=kicad_version,
                design=design,
            )
        )
    return findings


def normalize_erc_text(
    text: str,
    *,
    design: Any | None = None,
    source_name: str | None = None,
) -> list[Finding]:
    """Best-effort parse of classic KiCad ``.rpt`` ERC text."""
    findings: list[Finding] = []
    current_type = "unknown"
    current_desc = ""
    current_items: list[dict[str, Any]] = []
    sheet_path = "/"

    def flush() -> None:
        nonlocal current_type, current_desc, current_items
        if not current_desc and not current_items:
            return
        findings.append(
            _violation_to_finding(
                {
                    "type": current_type,
                    "description": current_desc or current_type,
                    "severity": "error",
                    "items": current_items,
                },
                sheet_path=sheet_path,
                report_source=source_name or "",
                kicad_version="",
                design=design,
            )
        )
        current_type = "unknown"
        current_desc = ""
        current_items = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("***** Sheet"):
            flush()
            sheet_path = line.split("Sheet", 1)[-1].strip() or "/"
            continue
        match = _TEXT_VIOLATION.match(line.strip())
        if match:
            flush()
            current_type = match.group("type").strip()
            current_desc = match.group("desc").strip()
            continue
        match = _TEXT_ERRTYPE.match(line.strip())
        if match:
            flush()
            current_type = "errtype"
            current_desc = match.group("desc").strip()
            continue
        item_match = _TEXT_ITEM.match(line)
        if item_match and (current_desc or current_type != "unknown"):
            current_items.append({"description": item_match.group("body").strip()})
            continue
    flush()
    return findings


def _iter_violations(report: dict[str, Any]):
    """Yield ``(sheet_path, violation)`` from nested or flat ERC JSON."""
    sheets = report.get("sheets")
    if isinstance(sheets, list):
        for sheet in sheets:
            if not isinstance(sheet, dict):
                continue
            sheet_path = str(sheet.get("path") or "/")
            for violation in sheet.get("violations") or []:
                if isinstance(violation, dict):
                    yield sheet_path, violation
        return

    # Older / alternate flat shapes
    for key in ("violations", "errors"):
        items = report.get(key)
        if isinstance(items, list):
            for violation in items:
                if isinstance(violation, dict):
                    yield "/", violation
            return


def _violation_to_finding(
    violation: dict[str, Any],
    *,
    sheet_path: str,
    report_source: str,
    kicad_version: str,
    design: Any | None,
) -> Finding:
    vtype = str(violation.get("type") or "unknown")
    description = str(violation.get("description") or vtype)
    severity = _SEVERITY_MAP.get(str(violation.get("severity") or "error").lower(), Severity.ERROR)
    items = violation.get("items") or []
    if not isinstance(items, list):
        items = []

    objects = collect_objects_from_items(items, design=design, sheet_path=sheet_path)
    excerpt = description
    if report_source:
        excerpt = f"{report_source}: {description}"

    evidence = EvidenceRef(
        id=f"erc:{vtype}",
        kind="erc",
        title=f"KiCad ERC: {vtype}",
        uri=report_source or None,
        excerpt=excerpt[:500],
        confidence=1.0,
    )
    if kicad_version:
        # Keep provenance in evidence without expanding Finding schema.
        evidence = evidence.model_copy(
            update={"excerpt": f"[kicad {kicad_version}] {evidence.excerpt}"}
        )

    return Finding(
        rule_id=f"erc.{vtype}",
        severity=severity,
        objects=objects,
        explanation=description,
        evidence_refs=[evidence],
        confidence=1.0,
        source="kicad_erc",
    )
