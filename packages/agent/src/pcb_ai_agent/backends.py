"""Proposal backend protocol — deterministic MVP with an LLM-shaped seam.

Guardrails
----------
* Backends may only emit typed ``Operation`` objects. They must never write
  production CAD files or call external mutation APIs.
* The default ``DeterministicRemediationBackend`` needs no network or LLM key.
* An LLM backend can implement ``ProposalBackend.propose`` later; the planner
  still gates on ``enabled`` and applies only via the transaction compiler on
  an IR copy / temp branch.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pcb_ai_circuit_ir.models import Design, Finding, Operation

from pcb_ai_agent.remediation import map_findings_to_operations


@runtime_checkable
class ProposalBackend(Protocol):
    """Pluggable propose() surface (deterministic today, LLM later)."""

    def propose(self, design: Design, findings: list[Finding]) -> list[Operation]:
        """Return typed remediation operations for the given findings."""


class DeterministicRemediationBackend:
    """Rule→operation mapper. No external LLM; suitable for Phase A MVP."""

    def propose(self, design: Design, findings: list[Finding]) -> list[Operation]:
        return map_findings_to_operations(design, findings)
