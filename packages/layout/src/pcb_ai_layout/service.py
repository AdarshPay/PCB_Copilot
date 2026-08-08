"""End-to-end layout job: verify → board skeleton → place/route → emit PCB."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from pcb_ai_agent.telemetry import DecisionTelemetry
from pcb_ai_circuit_ir.models import Design, Finding
from pcb_ai_kicad_adapter import (
    schematic_design_to_board_skeleton,
    write_pcb,
)
from pcb_ai_layout.backend import LayoutBackend
from pcb_ai_layout.grid_backend import GridLayoutBackend
from pcb_ai_pcb_ir.models import Board
from pcb_ai_verification import run_rules

_TELEMETRY = DecisionTelemetry()


@dataclass
class LayoutJobResult:
    board: Board
    pcb_path: Path
    design: Design
    rule_findings: list[Finding]
    proposal_id: str
    unrouted_nets: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "pcb_path": str(self.pcb_path),
            "proposal_id": self.proposal_id,
            "unrouted_nets": list(self.unrouted_nets),
            "metadata": dict(self.metadata),
            "layout_findings": len(self.board.findings),
            "rule_findings": len(self.rule_findings),
            "production_mutation": False,
            "human_approval_required": True,
        }


def load_design_from_source(source: Path | str) -> Design:
    """Load Circuit IR from a ``.kicad_sch`` or Design JSON path."""
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"Layout source not found: {path}")
    if path.suffix.lower() == ".kicad_sch":
        from pcb_ai_kicad_adapter import ingest_schematic

        return ingest_schematic(path)
    return Design.model_validate(json.loads(path.read_text(encoding="utf-8")))


def run_layout_job(
    design: Design,
    dest_dir: Path | str,
    *,
    pcb_name: str = "layout.kicad_pcb",
    backend: LayoutBackend | None = None,
    register_proposal: bool = True,
    telemetry: DecisionTelemetry | None = None,
    proposal_id: str | None = None,
) -> LayoutJobResult:
    """Place/route ``design`` and write a temp ``.kicad_pcb`` under ``dest_dir``.

    Never overwrites a caller's production CAD path by itself — callers must
    pass an isolated ``dest_dir``. Artifacts are always branch/temp-only.
    """
    out_dir = Path(dest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pcb_path = (out_dir / pcb_name).resolve()

    rule_findings = run_rules(design)
    skeleton = schematic_design_to_board_skeleton(design)
    engine = backend or GridLayoutBackend()
    board = engine.layout(design, skeleton)
    write_pcb(board, pcb_path)

    job_proposal_id = proposal_id or str(uuid4())
    if register_proposal:
        tel = telemetry or _TELEMETRY
        tel.register_proposal(
            design_id=design.id,
            operation_ids=[op.id for op in board.operations],
            rule_ids=sorted({f.rule_id for f in [*rule_findings, *board.findings]}),
            proposal_id=job_proposal_id,
        )

    return LayoutJobResult(
        board=board,
        pcb_path=pcb_path,
        design=design,
        rule_findings=rule_findings,
        proposal_id=job_proposal_id,
        unrouted_nets=list(board.unrouted_nets),
        metadata={
            "production_mutation": False,
            "layout_backend": board.attributes.get("layout_backend", "grid_mvp"),
            "footprint_count": len(board.footprints),
            "track_count": len(board.tracks),
            "via_count": len(board.vias),
            "placed": sum(1 for f in board.footprints if f.placement.placed),
            "operation_count": len(board.operations),
        },
    )
