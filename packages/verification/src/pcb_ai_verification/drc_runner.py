"""Run KiCad board DRC via local CLI / Docker, or parse offline fixtures."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pcb_ai_circuit_ir.models import Finding

from pcb_ai_verification.drc_parse import parse_drc_report

DrcMode = Literal["auto", "docker", "local", "mock"]

DEFAULT_DOCKER_IMAGE = os.environ.get("PCB_AI_KICAD_IMAGE", "pcb-ai-kicad-cli:local")


@dataclass(frozen=True)
class DrcRunResult:
    findings: list[Finding]
    report_path: Path | None
    mode: str
    command: list[str] | None = None
    returncode: int | None = None
    stderr: str | None = None


class DrcRunnerError(RuntimeError):
    pass


def resolve_drc_mode(explicit: DrcMode | None = None) -> DrcMode:
    if explicit is not None:
        return explicit
    env = os.environ.get("PCB_AI_DRC_MODE", "auto").strip().lower()
    if env in {"auto", "docker", "local", "mock"}:
        return env  # type: ignore[return-value]
    return "auto"


def run_board_drc(
    board: str | Path | None = None,
    *,
    report_path: str | Path | None = None,
    mode: DrcMode | None = None,
    docker_image: str | None = None,
    work_dir: str | Path | None = None,
) -> DrcRunResult:
    """Run DRC or parse an existing report into Findings."""
    chosen = resolve_drc_mode(mode)

    if report_path is not None:
        path = Path(report_path)
        findings = parse_drc_report(path)
        return DrcRunResult(findings=findings, report_path=path, mode="report")

    if chosen == "mock":
        mock = os.environ.get("PCB_AI_DRC_MOCK_REPORT")
        if not mock:
            raise DrcRunnerError("DRC mock mode requires report_path or PCB_AI_DRC_MOCK_REPORT")
        path = Path(mock)
        return DrcRunResult(findings=parse_drc_report(path), report_path=path, mode="mock")

    if board is None:
        raise DrcRunnerError("board path is required when not using a prebuilt report")

    pcb_path = Path(board).resolve()
    if not pcb_path.is_file():
        raise DrcRunnerError(f"Board not found: {pcb_path}")

    out_dir = Path(work_dir) if work_dir else pcb_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_report = out_dir / f"{pcb_path.stem}_drc.json"
    cmd = ["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(out_report), str(pcb_path)]

    if chosen in {"auto", "local"} and shutil.which("kicad-cli"):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and out_report.is_file():
            return DrcRunResult(
                findings=parse_drc_report(out_report),
                report_path=out_report,
                mode="local",
                command=cmd,
                returncode=proc.returncode,
                stderr=proc.stderr,
            )
        if chosen == "local":
            raise DrcRunnerError(f"kicad-cli pcb drc failed: {proc.stderr}")

    image = docker_image or DEFAULT_DOCKER_IMAGE
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{pcb_path.parent}:/work",
        image,
        "pcb",
        "drc",
        "--format",
        "json",
        "-o",
        f"/work/{out_report.name}",
        f"/work/{pcb_path.name}",
    ]
    if chosen in {"auto", "docker"} and shutil.which("docker"):
        proc = subprocess.run(docker_cmd, capture_output=True, text=True, check=False)
        if out_report.is_file():
            return DrcRunResult(
                findings=parse_drc_report(out_report),
                report_path=out_report,
                mode="docker",
                command=docker_cmd,
                returncode=proc.returncode,
                stderr=proc.stderr,
            )
        if chosen == "docker":
            raise DrcRunnerError(f"docker pcb drc failed: {proc.stderr}")

    raise DrcRunnerError(
        "No DRC runner available; pass report_path for offline fixture mode"
    )
