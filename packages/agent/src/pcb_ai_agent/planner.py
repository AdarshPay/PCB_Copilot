"""Structured planner interface.

Guardrails
----------
* Default ``enabled=False`` — proposing raises ``PlannerDisabled`` so CAD/LLM
  writes stay off until an explicit opt-in.
* When enabled, the MVP uses a deterministic remediation backend (no external
  LLM required). Plug in another ``ProposalBackend`` for LLM-backed proposals.
* Returned operations are typed IR edits only. Apply them with the transaction
  compiler on a Design copy / temp branch — never mutate production CAD here.
"""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design, Finding, Operation

from pcb_ai_agent.backends import DeterministicRemediationBackend, ProposalBackend


class PlannerDisabled(RuntimeError):
    pass


class Planner:
    """Propose typed operations from findings. MVP keeps this off by default."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        backend: ProposalBackend | None = None,
    ) -> None:
        self.enabled = enabled
        self.backend: ProposalBackend = backend or DeterministicRemediationBackend()

    def propose(self, design: Design, findings: list[Finding]) -> list[Operation]:
        if not self.enabled:
            raise PlannerDisabled(
                "LLM planner is disabled for the verification-first MVP. "
                f"Received {len(findings)} findings for design {design.id}."
            )
        return list(self.backend.propose(design, findings))
