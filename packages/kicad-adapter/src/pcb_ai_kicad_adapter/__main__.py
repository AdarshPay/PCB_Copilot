"""CLI: ingest a KiCad schematic into Circuit IR and optionally run rules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcb-ai-kicad",
        description="Parse a KiCad schematic into Circuit IR (verification-first; no LLM).",
    )
    parser.add_argument("schematic", type=Path, help="Path to a .kicad_sch file")
    parser.add_argument(
        "--design-id",
        default=None,
        help="Override Circuit IR design id (default: kicad.<stem>)",
    )
    parser.add_argument(
        "--rules",
        action="store_true",
        help="Run deterministic verification rules after ingest",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Emit a machine-readable ReviewReport JSON (implies rules)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Write an HTML semantic review report to this path (implies rules)",
    )
    parser.add_argument(
        "--emit",
        type=Path,
        default=None,
        help="Write a semantic round-trip .kicad_sch to this path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write Circuit IR / report JSON to this path (default: stdout)",
    )
    args = parser.parse_args(argv)

    from pcb_ai_kicad_adapter.emit import emit_schematic_text
    from pcb_ai_kicad_adapter.normalize import ingest_schematic

    design = ingest_schematic(args.schematic, design_id=args.design_id)

    if args.report or args.html is not None:
        from pcb_ai_verification import build_review_report, render_html_report

        report = build_review_report(design)
        if args.html is not None:
            args.html.parent.mkdir(parents=True, exist_ok=True)
            args.html.write_text(render_html_report(report, design), encoding="utf-8")
        if args.report:
            payload: dict = report.model_dump(mode="json", by_alias=True)
        else:
            payload = {
                "design_id": design.id,
                "finding_count": len(report.findings),
                "html": str(args.html),
            }
    elif args.rules:
        from pcb_ai_verification import run_rules

        findings = run_rules(design)
        payload = {
            "design": design.model_dump(mode="json", by_alias=True),
            "findings": [f.model_dump(mode="json", by_alias=True) for f in findings],
        }
    else:
        payload = design.model_dump(mode="json", by_alias=True)

    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")

    if args.emit:
        args.emit.write_text(emit_schematic_text(design), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
