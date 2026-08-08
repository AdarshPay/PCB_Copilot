"""Offline CI hardware-check command (ingest + rules + ERC/DRC fixtures)."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_benchmarks.ci_check import (
    EXIT_HARD_FAILURE,
    EXIT_OK,
    main,
    run_ci_hardware_check,
)
from pcb_ai_verification import run_board_drc
from tests.conftest import KICAD_FIXTURES

RC_SCH = KICAD_FIXTURES / "rc_divider.kicad_sch"
ERC_JSON = KICAD_FIXTURES / "rc_divider_erc.json"
DRC_JSON = KICAD_FIXTURES / "boards" / "rc_divider_drc.json"


def test_ci_hardware_check_sample_ok() -> None:
    result = run_ci_hardware_check(RC_SCH, erc_report=ERC_JSON, drc_report=DRC_JSON)
    assert result.exit_code == EXIT_OK
    assert result.manifest["ok"] is True
    assert result.manifest["summary"]["rule_blocking_count"] == 0
    assert result.manifest["summary"]["erc_finding_count"] == 3
    assert result.manifest["summary"]["erc_mode"] == "report"
    assert result.manifest["summary"]["drc_finding_count"] == 2
    assert result.manifest["summary"]["drc_mode"] == "report"
    assert result.design is not None


def test_ci_hardware_check_no_erc_no_drc() -> None:
    result = run_ci_hardware_check(RC_SCH, erc_report=None, drc_report=None)
    assert result.exit_code == EXIT_OK
    assert result.manifest["summary"]["erc_finding_count"] == 0
    assert result.manifest["summary"]["drc_finding_count"] == 0
    assert result.manifest["erc_report"] is None
    assert result.manifest["drc_report"] is None


def test_ci_hardware_check_missing_schematic(tmp_path: Path) -> None:
    result = run_ci_hardware_check(tmp_path / "missing.kicad_sch")
    assert result.exit_code == EXIT_HARD_FAILURE
    assert result.manifest["ok"] is False


def test_ci_hardware_check_cli_writes_manifest(tmp_path: Path) -> None:
    out = tmp_path / "ci-hardware-check.json"
    code = main(
        [
            "--schematic",
            str(RC_SCH),
            "--erc-report",
            str(ERC_JSON),
            "--drc-report",
            str(DRC_JSON),
            "-o",
            str(out),
        ]
    )
    assert code == EXIT_OK
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert '"kind": "ci_hardware_check"' in text
    assert '"ok": true' in text
    assert '"drc_finding_count": 2' in text


def test_ci_hardware_check_cli_missing_erc(tmp_path: Path) -> None:
    out = tmp_path / "fail.json"
    code = main(
        [
            "--schematic",
            str(RC_SCH),
            "--erc-report",
            str(tmp_path / "nope.json"),
            "--no-drc",
            "-o",
            str(out),
        ]
    )
    assert code == EXIT_HARD_FAILURE
    assert out.is_file()


def test_ci_hardware_check_cli_missing_drc(tmp_path: Path) -> None:
    out = tmp_path / "fail-drc.json"
    code = main(
        [
            "--schematic",
            str(RC_SCH),
            "--no-erc",
            "--drc-report",
            str(tmp_path / "nope-drc.json"),
            "-o",
            str(out),
        ]
    )
    assert code == EXIT_HARD_FAILURE
    assert out.is_file()


def test_run_board_drc_offline_fixture() -> None:
    result = run_board_drc(report_path=DRC_JSON)
    assert result.mode == "report"
    assert len(result.findings) == 2
    assert result.findings[0].source == "kicad_drc"
    assert result.findings[0].rule_id == "drc.clearance"
