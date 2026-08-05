"""Agent package — deterministic typed remediations (LLM backend pluggable).

Guardrails: planner defaults to enabled=False; when enabled, proposals are typed
Operations only and must be applied via the transaction compiler on an IR copy /
temp branch — never directly to production CAD.
"""

from pcb_ai_agent.backends import DeterministicRemediationBackend, ProposalBackend
from pcb_ai_agent.planner import Planner, PlannerDisabled
from pcb_ai_agent.remediation import SUPPORTED_RULE_IDS, map_findings_to_operations

__all__ = [
    "DeterministicRemediationBackend",
    "Planner",
    "PlannerDisabled",
    "ProposalBackend",
    "SUPPORTED_RULE_IDS",
    "map_findings_to_operations",
]
