"""Reproducible benchmark / mutation-suite run manifests."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pcb_ai_circuit_ir.models import Design
from pcb_ai_verification import run_rules


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseResult(Model):
    case_id: str
    base_design_id: str
    mutation: str | None = None
    expected_rule_id: str | None = None
    detected_rule_ids: list[str] = Field(default_factory=list)
    passed: bool
    finding_count: int = 0
    notes: str | None = None


class RunManifest(Model):
    """Machine-readable record of a deterministic verification benchmark run."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    tool_versions: dict[str, str] = Field(default_factory=dict)
    rule_pack: str = "v0"
    dataset: str = "golden+mutations"
    cases: list[CaseResult] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)

    def write_json(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return out


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def default_tool_versions() -> dict[str, str]:
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pcb-ai-benchmarks": "0.1.0",
        "rule_pack": "v0",
    }
    try:
        import pcb_ai_circuit_ir

        versions["pcb-ai-circuit-ir"] = getattr(pcb_ai_circuit_ir, "__version__", "0.1.0")
    except Exception:
        pass
    try:
        import pcb_ai_verification

        versions["pcb-ai-verification"] = getattr(pcb_ai_verification, "__version__", "0.1.0")
    except Exception:
        pass
    return versions


def evaluate_clean_case(design: Design, *, case_id: str) -> CaseResult:
    findings = run_rules(design)
    from tests.mutation.ir_mutators import FIRST_PACK_RULE_IDS

    detected = sorted({f.rule_id for f in findings if f.rule_id in FIRST_PACK_RULE_IDS})
    return CaseResult(
        case_id=case_id,
        base_design_id=design.id,
        mutation=None,
        expected_rule_id=None,
        detected_rule_ids=detected,
        passed=len(detected) == 0,
        finding_count=len(findings),
        notes="clean design should have no first-pack findings",
    )


def evaluate_mutation_case(
    design: Design,
    *,
    case_id: str,
    mutation: str,
    expected_rule_id: str,
) -> CaseResult:
    findings = run_rules(design)
    from tests.mutation.ir_mutators import FIRST_PACK_RULE_IDS

    detected = sorted({f.rule_id for f in findings if f.rule_id in FIRST_PACK_RULE_IDS})
    passed = detected == [expected_rule_id]
    return CaseResult(
        case_id=case_id,
        base_design_id=design.id if not mutation else design.id,
        mutation=mutation,
        expected_rule_id=expected_rule_id,
        detected_rule_ids=detected,
        passed=passed,
        finding_count=len(findings),
        notes="single-fault precision: exactly the expected first-pack rule",
    )


def build_manifest(
    cases: list[CaseResult],
    *,
    artifact_paths: list[Path] | None = None,
    dataset: str = "golden+mutations",
) -> RunManifest:
    passed = sum(1 for c in cases if c.passed)
    failed = len(cases) - passed
    hashes: dict[str, str] = {}
    for path in artifact_paths or []:
        if path.is_file():
            hashes[str(path.as_posix())] = _file_sha256(path)

    return RunManifest(
        tool_versions=default_tool_versions(),
        dataset=dataset,
        cases=cases,
        summary={
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / len(cases)) if cases else 0.0,
        },
        artifact_hashes=hashes,
    )


def run_first_pack_benchmark(fixtures_dir: Path) -> RunManifest:
    """Run clean + single-fault mutation cases against golden JSON fixtures."""
    import sys

    repo_root = fixtures_dir.resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from tests.mutation.ir_mutators import (
        FIRST_PACK_RULE_IDS,
        mutate_duplicate_reference,
        mutate_missing_footprint,
        mutate_missing_open_drain_pullup,
        mutate_missing_pin,
        mutate_missing_power_source,
        mutate_output_conflict,
        mutate_reversed_polarity,
        mutate_undriven_enable,
        mutate_undriven_input,
        mutate_voltage_domain_conflict,
    )

    golden_dir = fixtures_dir / "golden"
    cases: list[CaseResult] = []
    artifact_paths: list[Path] = []

    clean_names = (
        "rc_divider.json",
        "i2c_sensor.json",
        "ldo_rail.json",
        "uart_bridge.json",
        "can_transceiver.json",
        "rs485_link.json",
        "esd_connector.json",
        "buck_regulator.json",
        "programming_header.json",
        "spi_flash.json",
    )
    for name in clean_names:
        path = golden_dir / name
        artifact_paths.append(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        design = Design.model_validate(data)
        cases.append(evaluate_clean_case(design, case_id=f"clean:{path.stem}"))

        mutations = [
            ("duplicate_reference", mutate_duplicate_reference, "struct.unique_references"),
            ("missing_pin", mutate_missing_pin, "struct.pin_existence"),
            ("missing_footprint", mutate_missing_footprint, "struct.footprint_presence"),
            ("output_conflict", mutate_output_conflict, "elec.output_conflict"),
            ("undriven_input", mutate_undriven_input, "elec.undriven_input"),
            ("undriven_enable", mutate_undriven_enable, "elec.undriven_input"),
            ("missing_power_source", mutate_missing_power_source, "elec.power_source"),
            ("missing_open_drain_pullup", mutate_missing_open_drain_pullup, "elec.open_drain_pullup"),
            ("voltage_domain_conflict", mutate_voltage_domain_conflict, "elec.voltage_domain"),
            ("reversed_polarity", mutate_reversed_polarity, "elec.polarity"),
        ]
        for mut_name, mutator, expected in mutations:
            mutant = mutator(design)
            result = evaluate_mutation_case(
                mutant,
                case_id=f"{path.stem}:{mut_name}",
                mutation=mut_name,
                expected_rule_id=expected,
            )
            result = result.model_copy(update={"base_design_id": design.id})
            cases.append(result)

    conflict_path = golden_dir / "output_conflict.json"
    if conflict_path.is_file():
        artifact_paths.append(conflict_path)
        conflict = Design.model_validate(json.loads(conflict_path.read_text(encoding="utf-8")))
        findings = run_rules(conflict)
        detected = sorted(
            {f.rule_id for f in findings if f.rule_id in FIRST_PACK_RULE_IDS}
        )
        cases.append(
            CaseResult(
                case_id="fixture:output_conflict",
                base_design_id=conflict.id,
                mutation="fixture_output_conflict",
                expected_rule_id="elec.output_conflict",
                detected_rule_ids=detected,
                passed=detected == ["elec.output_conflict"],
                finding_count=len(findings),
            )
        )

    return build_manifest(cases, artifact_paths=artifact_paths)
