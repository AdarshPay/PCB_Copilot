"""Structured planner interface. Disabled until deterministic path is solid."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design, Finding, Operation


class PlannerDisabled(RuntimeError):
    pass


class Planner:
    """Propose typed operations from findings. MVP keeps this off by default."""

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    def propose(self, design: Design, findings: list[Finding]) -> list[Operation]:
        if not self.enabled:
            raise PlannerDisabled(
                "LLM planner is disabled for the verification-first MVP. "
                f"Received {len(findings)} findings for design {design.id}."
            )
        return []
