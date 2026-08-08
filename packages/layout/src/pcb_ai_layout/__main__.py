"""CLI: python -m pcb_ai_layout layout <schematic|golden.json> --out DIR"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pcb_ai_circuit_ir.models import Design
from pcb_ai_layout.service import run_layout_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pcb-ai-layout", description="Phase B MVP layout")
    sub = parser.add_subparsers(dest="cmd", required=True)

    layout_p = sub.add_parser("layout", help="Place/route a schematic or golden IR JSON")
    layout_p.add_argument("source", type=Path, help=".kicad_sch or Design JSON")
    layout_p.add_argument("-o", "--out", type=Path, required=True, help="Output directory")
    layout_p.add_argument("--pcb-name", default="layout.kicad_pcb")

    args = parser.parse_args(argv)
    if args.cmd == "layout":
        source: Path = args.source
        if source.suffix.lower() == ".kicad_sch":
            from pcb_ai_kicad_adapter import ingest_schematic

            design = ingest_schematic(source)
        else:
            design = Design.model_validate(json.loads(source.read_text(encoding="utf-8")))
        result = run_layout_job(design, args.out, pcb_name=args.pcb_name)
        summary = {
            "pcb_path": str(result.pcb_path),
            "proposal_id": result.proposal_id,
            "unrouted_nets": result.unrouted_nets,
            "metadata": result.metadata,
            "layout_findings": len(result.board.findings),
            "rule_findings": len(result.rule_findings),
        }
        print(json.dumps(summary, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
