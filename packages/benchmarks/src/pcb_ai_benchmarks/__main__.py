"""CLI: run the first-pack mutation benchmark and write a run manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcb-ai-benchmark",
        description="Run deterministic first-pack mutation benchmark and emit a run manifest.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Path to tests/fixtures (default: <repo>/tests/fixtures)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("reports/run-manifest.json"),
        help="Where to write the run manifest JSON",
    )
    args = parser.parse_args(argv)

    fixtures = args.fixtures
    if fixtures is None:
        # packages/benchmarks/src/pcb_ai_benchmarks/__main__.py -> repo root
        fixtures = Path(__file__).resolve().parents[4] / "tests" / "fixtures"

    from pcb_ai_benchmarks.manifest import run_first_pack_benchmark

    manifest = run_first_pack_benchmark(fixtures)
    out = manifest.write_json(args.output)
    sys.stdout.write(json.dumps(manifest.summary, indent=2) + "\n")
    sys.stdout.write(f"wrote {out}\n")
    return 0 if manifest.summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
