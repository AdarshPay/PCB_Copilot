"""Benchmark run-manifest tests."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_benchmarks import run_first_pack_benchmark
from tests.conftest import FIXTURES


def test_first_pack_benchmark_manifest(tmp_path: Path) -> None:
    fixtures_dir = FIXTURES.parent  # tests/fixtures
    manifest = run_first_pack_benchmark(fixtures_dir)
    assert manifest.summary["total"] >= 37  # 4 clean + 4*9 mutations + conflict fixture
    assert manifest.summary["failed"] == 0
    assert manifest.summary["passed"] == manifest.summary["total"]
    assert manifest.artifact_hashes
    out = manifest.write_json(tmp_path / "run-manifest.json")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "tool_versions" in text
    assert "cases" in text
