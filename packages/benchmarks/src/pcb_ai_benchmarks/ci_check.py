"""CI hardware check: ingest + RULE_PACK_V0 (+ optional offline ERC/DRC fixtures).

Exit-code policy
----------------
* ``0`` — ingest succeeded; RULE_PACK has no blocking findings (``error`` /
  ``critical``); offline ERC/DRC paths (if enabled) parsed successfully.
* ``1`` — sample project unexpectedly has blocking RULE_PACK findings, or an
  offline ERC/DRC fixture could not be parsed / runner raised.
* ``2`` — hard failure (missing inputs, ingest/parse exception, I/O error).

Offline ERC/DRC findings from the intentional dirty fixtures are **not**
treated as CI failures: those fixtures smoke-test the parsers. RULE_PACK on the
clean sample schematic is the blocking oracle. Live ``kicad-cli pcb drc`` remains
optional via ``run_board_drc`` when KiCad/Docker is available.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pcb_ai_circuit_ir.models import Design, Finding, Severity

BLOCKING = {Severity.ERROR, Severity.CRITICAL}

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_HARD_FAILURE = 2


def _repo_root() -> Path:
    # packages/benchmarks/src/pcb_ai_benchmarks/ci_check.py -> repo root
    return Path(__file__).resolve().parents[4]


def _default_schematic() -> Path:
    return _repo_root() / "tests" / "fixtures" / "kicad" / "rc_divider.kicad_sch"


def _default_erc_report() -> Path:
    return _repo_root() / "tests" / "fixtures" / "kicad" / "rc_divider_erc.json"


def _default_drc_report() -> Path:
    return (
        _repo_root()
        / "tests"
        / "fixtures"
        / "kicad"
        / "boards"
        / "rc_divider_drc.json"
    )


def _finding_dump(finding: Finding) -> dict[str, Any]:
    return finding.model_dump(mode="json", by_alias=True)


def _tool_versions() -> dict[str, str]:
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pcb-ai-benchmarks": "0.1.0",
        "rule_pack": "v0",
    }
    for mod_name, key in (
        ("pcb_ai_circuit_ir", "pcb-ai-circuit-ir"),
        ("pcb_ai_verification", "pcb-ai-verification"),
        ("pcb_ai_kicad_adapter", "pcb-ai-kicad-adapter"),
    ):
        try:
            mod = __import__(mod_name)
            versions[key] = getattr(mod, "__version__", "0.1.0")
        except Exception:
            versions[key] = "unknown"
    return versions


@dataclass
class CiCheckResult:
    manifest: dict[str, Any]
    exit_code: int
    design: Design | None = None
    combined_findings: list[Finding] | None = None


def run_ci_hardware_check(
    schematic: Path,
    *,
    erc_report: Path | None = None,
    drc_report: Path | None = None,
    design_id: str | None = None,
) -> CiCheckResult:
    """Ingest schematic, run rules, optionally parse offline ERC/DRC fixtures."""
    from pcb_ai_kicad_adapter.normalize import ingest_schematic
    from pcb_ai_verification import (
        build_review_report,
        run_board_drc,
        run_rules,
        run_schematic_erc,
    )

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest: dict[str, Any] = {
        "id": str(uuid4()),
        "kind": "ci_hardware_check",
        "created_at": created_at,
        "schematic": str(schematic),
        "erc_report": str(erc_report) if erc_report else None,
        "drc_report": str(drc_report) if drc_report else None,
        "rule_pack": "v0",
        "tool_versions": _tool_versions(),
        "exit_policy": {
            "blocking_severities": sorted(s.value for s in BLOCKING),
            "rule_findings": "fail if any RULE_PACK finding has error/critical",
            "erc_findings": (
                "informational only when using the intentional ERC fixture; "
                "fail only if offline ERC parse/runner errors"
            ),
            "drc_findings": (
                "informational only when using the intentional DRC fixture; "
                "fail only if offline DRC parse/runner errors"
            ),
        },
        "ok": False,
        "design_id": None,
        "rule_findings": [],
        "erc_findings": [],
        "drc_findings": [],
        "review_summary": {},
        "summary": {},
        "errors": [],
    }

    if not schematic.is_file():
        manifest["errors"].append(f"schematic not found: {schematic}")
        manifest["summary"] = {"ok": False, "reason": "missing_schematic"}
        return CiCheckResult(manifest, EXIT_HARD_FAILURE)

    if erc_report is not None and not erc_report.is_file():
        manifest["errors"].append(f"erc report not found: {erc_report}")
        manifest["summary"] = {"ok": False, "reason": "missing_erc_report"}
        return CiCheckResult(manifest, EXIT_HARD_FAILURE)

    if drc_report is not None and not drc_report.is_file():
        manifest["errors"].append(f"drc report not found: {drc_report}")
        manifest["summary"] = {"ok": False, "reason": "missing_drc_report"}
        return CiCheckResult(manifest, EXIT_HARD_FAILURE)

    try:
        design = ingest_schematic(schematic, design_id=design_id)
    except Exception as exc:
        manifest["errors"].append(f"ingest failed: {exc}")
        manifest["summary"] = {"ok": False, "reason": "ingest_error"}
        return CiCheckResult(manifest, EXIT_HARD_FAILURE)

    manifest["design_id"] = design.id

    try:
        rule_findings = run_rules(design)
    except Exception as exc:
        manifest["errors"].append(f"rules failed: {exc}")
        manifest["summary"] = {"ok": False, "reason": "rules_error"}
        return CiCheckResult(manifest, EXIT_HARD_FAILURE, design=design)

    blocking = [f for f in rule_findings if f.severity in BLOCKING]
    manifest["rule_findings"] = [_finding_dump(f) for f in rule_findings]

    erc_findings: list[Finding] = []
    erc_mode: str | None = None
    if erc_report is not None:
        try:
            result = run_schematic_erc(report_path=erc_report, design=design)
            erc_findings = list(result.findings)
            erc_mode = result.mode
        except Exception as exc:
            manifest["errors"].append(f"offline ERC failed: {exc}")
            manifest["summary"] = {
                "ok": False,
                "reason": "erc_error",
                "rule_finding_count": len(rule_findings),
                "rule_blocking_count": len(blocking),
            }
            return CiCheckResult(
                manifest,
                EXIT_CHECK_FAILED,
                design=design,
                combined_findings=list(rule_findings),
            )

    manifest["erc_findings"] = [_finding_dump(f) for f in erc_findings]

    drc_findings: list[Finding] = []
    drc_mode: str | None = None
    if drc_report is not None:
        try:
            drc_result = run_board_drc(report_path=drc_report)
            drc_findings = list(drc_result.findings)
            drc_mode = drc_result.mode
        except Exception as exc:
            manifest["errors"].append(f"offline DRC failed: {exc}")
            manifest["summary"] = {
                "ok": False,
                "reason": "drc_error",
                "rule_finding_count": len(rule_findings),
                "rule_blocking_count": len(blocking),
                "erc_finding_count": len(erc_findings),
            }
            return CiCheckResult(
                manifest,
                EXIT_CHECK_FAILED,
                design=design,
                combined_findings=list(rule_findings) + erc_findings,
            )

    manifest["drc_findings"] = [_finding_dump(f) for f in drc_findings]

    combined = list(rule_findings) + erc_findings + drc_findings
    report = build_review_report(
        design,
        findings=combined,
        metadata={
            "kind": "ci_hardware_check",
            "erc_mode": erc_mode,
            "erc_report": str(erc_report) if erc_report else None,
            "drc_mode": drc_mode,
            "drc_report": str(drc_report) if drc_report else None,
        },
    )
    manifest["review_summary"] = report.summary

    rules_ok = len(blocking) == 0
    ok = rules_ok and not manifest["errors"]
    manifest["ok"] = ok
    manifest["summary"] = {
        "ok": ok,
        "rule_finding_count": len(rule_findings),
        "rule_blocking_count": len(blocking),
        "erc_finding_count": len(erc_findings),
        "erc_mode": erc_mode,
        "drc_finding_count": len(drc_findings),
        "drc_mode": drc_mode,
        "combined_finding_count": len(combined),
    }

    code = EXIT_OK if rules_ok else EXIT_CHECK_FAILED
    return CiCheckResult(manifest, code, design=design, combined_findings=combined)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcb-ai-ci-check",
        description=(
            "CI hardware check: ingest a sample KiCad schematic, run RULE_PACK_V0, "
            "and optionally parse offline ERC/DRC fixtures (no Docker KiCad)."
        ),
    )
    parser.add_argument(
        "--schematic",
        type=Path,
        default=None,
        help="Path to .kicad_sch (default: tests/fixtures/kicad/rc_divider.kicad_sch)",
    )
    parser.add_argument(
        "--erc-report",
        type=Path,
        default=None,
        help=(
            "Offline ERC JSON/.rpt path "
            "(default: tests/fixtures/kicad/rc_divider_erc.json; use --no-erc to skip)"
        ),
    )
    parser.add_argument(
        "--no-erc",
        action="store_true",
        help="Skip offline ERC fixture path",
    )
    parser.add_argument(
        "--drc-report",
        type=Path,
        default=None,
        help=(
            "Offline DRC JSON path "
            "(default: tests/fixtures/kicad/boards/rc_divider_drc.json; "
            "use --no-drc to skip)"
        ),
    )
    parser.add_argument(
        "--no-drc",
        action="store_true",
        help="Skip offline DRC fixture path",
    )
    parser.add_argument(
        "--design-id",
        default=None,
        help="Override Circuit IR design id",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("reports/ci-hardware-check.json"),
        help="Where to write the CI check manifest JSON",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Optional HTML review report path",
    )
    args = parser.parse_args(argv)

    schematic = args.schematic or _default_schematic()
    if args.no_erc:
        erc_report: Path | None = None
    else:
        erc_report = args.erc_report or _default_erc_report()
    if args.no_drc:
        drc_report: Path | None = None
    else:
        drc_report = args.drc_report or _default_drc_report()

    try:
        result = run_ci_hardware_check(
            schematic,
            erc_report=erc_report,
            drc_report=drc_report,
            design_id=args.design_id,
        )
    except Exception as exc:
        sys.stderr.write(f"ci hardware check crashed: {exc}\n")
        traceback.print_exc(file=sys.stderr)
        return EXIT_HARD_FAILURE

    manifest = result.manifest
    code = result.exit_code

    if args.html is not None and result.design is not None:
        try:
            from pcb_ai_verification import build_review_report, render_html_report

            findings = result.combined_findings or []
            report = build_review_report(result.design, findings=findings)
            args.html.parent.mkdir(parents=True, exist_ok=True)
            args.html.write_text(
                render_html_report(report, result.design), encoding="utf-8"
            )
            manifest["html"] = str(args.html)
        except Exception as exc:
            sys.stderr.write(f"html report failed: {exc}\n")
            if code == EXIT_OK:
                code = EXIT_HARD_FAILURE
            manifest.setdefault("errors", []).append(f"html failed: {exc}")
            manifest["ok"] = False

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    sys.stdout.write(json.dumps(manifest.get("summary", {}), indent=2) + "\n")
    sys.stdout.write(f"wrote {out}\n")
    if code != EXIT_OK:
        for err in manifest.get("errors") or []:
            sys.stderr.write(f"error: {err}\n")
        blocking_n = manifest.get("summary", {}).get("rule_blocking_count", 0)
        if blocking_n:
            sys.stderr.write(
                f"unexpected blocking RULE_PACK findings: {blocking_n}\n"
            )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
