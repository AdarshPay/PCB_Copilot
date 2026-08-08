"""CLI: python -m pcb_ai_layout layout <schematic|golden.json> --out DIR"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pcb_ai_layout.service import load_design_from_source, run_layout_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pcb-ai-layout", description="Phase B MVP layout")
    sub = parser.add_subparsers(dest="cmd", required=True)

    layout_p = sub.add_parser("layout", help="Place/route a schematic or golden IR JSON")
    layout_p.add_argument("source", type=Path, help=".kicad_sch or Design JSON")
    layout_p.add_argument("-o", "--out", type=Path, required=True, help="Output directory")
    layout_p.add_argument("--pcb-name", default="layout.kicad_pcb")
    layout_p.add_argument(
        "--no-register-proposal",
        action="store_true",
        help="Skip decision-telemetry proposal registration",
    )

    args = parser.parse_args(argv)
    if args.cmd == "layout":
        design = load_design_from_source(args.source)
        result = run_layout_job(
            design,
            args.out,
            pcb_name=args.pcb_name,
            register_proposal=not args.no_register_proposal,
        )
        summary = result.summary()
        summary_path = Path(args.out) / "layout-summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
