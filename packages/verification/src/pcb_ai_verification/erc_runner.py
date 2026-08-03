"""Run KiCad schematic ERC via local ``kicad-cli`` or the Docker image.

Offline / CI path: pass ``report_path`` or set ``PCB_AI_ERC_MODE=mock`` to skip
invoking KiCad and parse a pre-generated report instead.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pcb_ai_circuit_ir.models import Finding

from pcb_ai_verification.erc_parse import parse_erc_report

ErcMode = Literal["auto", "docker", "local", "mock"]

DEFAULT_DOCKER_IMAGE = os.environ.get("PCB_AI_KICAD_IMAGE", "pcb-ai-kicad-cli:local")
FALLBACK_DOCKER_IMAGE = os.environ.get("PCB_AI_KICAD_FALLBACK_IMAGE", "kicad/kicad:10.0")


@dataclass(frozen=True)
class ErcRunResult:
    findings: list[Finding]
    report_path: Path | None
    mode: str
    command: list[str] | None = None
    returncode: int | None = None
    stderr: str | None = None


class ErcRunnerError(RuntimeError):
    pass


def resolve_erc_mode(explicit: ErcMode | None = None) -> ErcMode:
    if explicit is not None:
        return explicit
    env = os.environ.get("PCB_AI_ERC_MODE", "auto").strip().lower()
    if env in {"auto", "docker", "local", "mock"}:
        return env  # type: ignore[return-value]
    return "auto"


def run_schematic_erc(
    schematic: str | Path | None = None,
    *,
    report_path: str | Path | None = None,
    design: Any | None = None,
    mode: ErcMode | None = None,
    docker_image: str | None = None,
    severity_all: bool = True,
    work_dir: str | Path | None = None,
) -> ErcRunResult:
    """Run ERC or parse an existing report into Findings.

    Parameters
    ----------
    schematic:
        Path to a ``.kicad_sch`` file. Required unless ``report_path`` is set or
        mode is ``mock`` with ``PCB_AI_ERC_MOCK_REPORT``.
    report_path:
        Existing ERC JSON/``.rpt`` to parse (offline path). When set, KiCad is
        not invoked.
    design:
        Optional Circuit IR Design for UUID/reference mapping.
    mode:
        ``auto`` tries local ``kicad-cli``, then Docker; ``mock`` never invokes
        KiCad.
    """
    chosen = resolve_erc_mode(mode)

    if report_path is not None:
        path = Path(report_path)
        findings = parse_erc_report(path, design=design)
        return ErcRunResult(findings=findings, report_path=path, mode="report")

    if chosen == "mock":
        mock = report_path or os.environ.get("PCB_AI_ERC_MOCK_REPORT")
        if not mock:
            raise ErcRunnerError(
                "ERC mock mode requires report_path or PCB_AI_ERC_MOCK_REPORT"
            )
        path = Path(mock)
        findings = parse_erc_report(path, design=design)
        return ErcRunResult(findings=findings, report_path=path, mode="mock")

    if schematic is None:
        raise ErcRunnerError("schematic path is required when not using a prebuilt report")

    sch_path = Path(schematic).resolve()
    if not sch_path.is_file():
        raise ErcRunnerError(f"Schematic not found: {sch_path}")

    if work_dir is not None:
        out_dir = Path(work_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_report = out_dir / f"{sch_path.stem}_erc.json"
    else:
        # Write beside the schematic so Docker bind-mounts stay simple.
        out_report = sch_path.parent / f"{sch_path.stem}_erc.json"

    if chosen == "local":
        return _run_local(sch_path, out_report, design=design, severity_all=severity_all)
    if chosen == "docker":
        return _run_docker(
            sch_path,
            out_report,
            design=design,
            severity_all=severity_all,
            docker_image=docker_image,
        )

    # auto
    if shutil.which("kicad-cli"):
        try:
            return _run_local(sch_path, out_report, design=design, severity_all=severity_all)
        except ErcRunnerError:
            pass
    if shutil.which("docker"):
        try:
            return _run_docker(
                sch_path,
                out_report,
                design=design,
                severity_all=severity_all,
                docker_image=docker_image,
            )
        except ErcRunnerError:
            pass
    raise ErcRunnerError(
        "Neither local kicad-cli nor Docker ERC could run. "
        "Use mode='mock' with a fixture report, or set PCB_AI_ERC_MODE=mock."
    )


def _erc_cli_args(schematic_name: str, output_name: str, *, severity_all: bool) -> list[str]:
    args = [
        "sch",
        "erc",
        "--format",
        "json",
        "--output",
        output_name,
    ]
    if severity_all:
        args.append("--severity-all")
    args.append(schematic_name)
    return args


def _run_local(
    sch_path: Path,
    out_report: Path,
    *,
    design: Any | None,
    severity_all: bool,
) -> ErcRunResult:
    cli = shutil.which("kicad-cli")
    if not cli:
        raise ErcRunnerError("kicad-cli not found on PATH")
    out_report.parent.mkdir(parents=True, exist_ok=True)
    # Prefer absolute --output so the report lands exactly where we expect.
    cmd = [cli, *_erc_cli_args(str(sch_path), str(out_report), severity_all=severity_all)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not out_report.is_file():
        raise ErcRunnerError(
            f"kicad-cli failed (rc={completed.returncode}): {completed.stderr or completed.stdout}"
        )
    findings = parse_erc_report(out_report, design=design)
    return ErcRunResult(
        findings=findings,
        report_path=out_report,
        mode="local",
        command=cmd,
        returncode=completed.returncode,
        stderr=completed.stderr or None,
    )


def _run_docker(
    sch_path: Path,
    out_report: Path,
    *,
    design: Any | None,
    severity_all: bool,
    docker_image: str | None,
) -> ErcRunResult:
    if not shutil.which("docker"):
        raise ErcRunnerError("docker not found on PATH")

    images: list[str] = []
    if docker_image:
        images.append(docker_image)
    for candidate in (DEFAULT_DOCKER_IMAGE, FALLBACK_DOCKER_IMAGE):
        if candidate not in images:
            images.append(candidate)

    host_dir = sch_path.parent.resolve()
    # Keep the container output filename stable inside /work.
    container_out = out_report.name if out_report.parent.resolve() == host_dir else f"{sch_path.stem}_erc.json"
    host_out = host_dir / container_out

    last_error = ""
    for image in images:
        # Official kicad/kicad and pcb-ai-kicad-cli set ENTRYPOINT to kicad-cli.
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{host_dir}:/work",
            "-w",
            "/work",
            image,
            *_erc_cli_args(sch_path.name, container_out, severity_all=severity_all),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if host_out.is_file():
            if host_out.resolve() != out_report.resolve():
                out_report.parent.mkdir(parents=True, exist_ok=True)
                out_report.write_text(host_out.read_text(encoding="utf-8"), encoding="utf-8")
                report = out_report
            else:
                report = host_out
            findings = parse_erc_report(report, design=design)
            return ErcRunResult(
                findings=findings,
                report_path=report,
                mode="docker",
                command=cmd,
                returncode=completed.returncode,
                stderr=completed.stderr or None,
            )
        last_error = completed.stderr or completed.stdout or f"rc={completed.returncode}"

    raise ErcRunnerError(f"Docker ERC failed for images {images}: {last_error}")
