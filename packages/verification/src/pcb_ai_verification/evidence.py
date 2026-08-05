"""Optional post-pass: attach curated evidence to rule findings."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Finding


def attach_evidence(
    findings: list[Finding],
    *,
    store=None,
) -> list[Finding]:
    """Enrich findings with the offline evidence catalog after ``run_rules``.

    Thin wrapper around ``pcb_ai_evidence.attach_to_findings`` so callers can
    keep rule bodies unchanged and enrich in a separate step.
    """
    from pcb_ai_evidence import attach_to_findings

    return attach_to_findings(findings, store=store)
