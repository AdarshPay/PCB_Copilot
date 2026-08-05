"""Build machine-readable semantic review reports from Circuit IR + findings."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pcb_ai_circuit_ir.models import Design, Finding, Net, NetFragment, Operation, ReviewReport
from pcb_ai_transactions.compiler import apply_operations, semantic_diff
from pcb_ai_verification.engine import run_rules


def _endpoint_label(component_ref: str, pin_number: str) -> str:
    return f"{component_ref}.{pin_number}"


def _net_to_fragment(
    net: Net,
    *,
    phase: str,
    related_finding_ids: list[str] | None = None,
) -> NetFragment:
    return NetFragment(
        net_name=net.name,
        phase=phase,
        endpoints=[_endpoint_label(ep.component_ref, ep.pin_number) for ep in net.endpoints],
        net_class=net.net_class.value if net.net_class else None,
        voltage_domain=net.voltage_domain,
        protocol=net.protocol,
        related_finding_ids=list(related_finding_ids or []),
    )


def _nets_by_name(design: Design) -> dict[str, Net]:
    return {net.name: net for net in design.nets}


def _finding_net_names(finding: Finding, design: Design) -> set[str]:
    """Infer nets related to a finding from object labels and endpoint refs."""
    net_names = {net.name for net in design.nets}
    related: set[str] = set()
    for obj in finding.objects:
        if obj in net_names:
            related.add(obj)
            continue
        # Match component.pin style against endpoints.
        if "." in obj:
            for net in design.nets:
                for ep in net.endpoints:
                    if _endpoint_label(ep.component_ref, ep.pin_number) == obj:
                        related.add(net.name)
    return related


def collect_net_fragments(
    design: Design,
    findings: list[Finding],
    *,
    after: Design | None = None,
) -> list[NetFragment]:
    """Capture current (and optional before/after) net neighborhoods for findings."""
    before_nets = _nets_by_name(design)
    after_nets = _nets_by_name(after) if after is not None else {}
    finding_ids_by_net: dict[str, list[str]] = {}
    for finding in findings:
        for name in _finding_net_names(finding, design):
            finding_ids_by_net.setdefault(name, []).append(finding.id)
        if after is not None:
            for name in _finding_net_names(finding, after):
                finding_ids_by_net.setdefault(name, []).append(finding.id)

    fragments: list[NetFragment] = []
    for net_name in sorted(finding_ids_by_net):
        related = sorted(set(finding_ids_by_net[net_name]))
        if after is None:
            net = before_nets.get(net_name)
            if net is not None:
                fragments.append(_net_to_fragment(net, phase="current", related_finding_ids=related))
            continue
        before = before_nets.get(net_name)
        after_net = after_nets.get(net_name)
        if before is not None:
            fragments.append(_net_to_fragment(before, phase="before", related_finding_ids=related))
        if after_net is not None:
            fragments.append(_net_to_fragment(after_net, phase="after", related_finding_ids=related))
        if before is None and after_net is None:
            continue
    return fragments


def summarize_findings(findings: list[Finding]) -> dict[str, Any]:
    by_severity = Counter(f.severity.value for f in findings)
    by_rule = Counter(f.rule_id for f in findings)
    by_source = Counter(f.source for f in findings)
    return {
        "finding_count": len(findings),
        "by_severity": dict(sorted(by_severity.items())),
        "by_rule": dict(sorted(by_rule.items())),
        "by_source": dict(sorted(by_source.items())),
    }


def build_review_report(
    design: Design,
    *,
    findings: list[Finding] | None = None,
    operations: list[Operation] | None = None,
    after_design: Design | None = None,
    metadata: dict[str, Any] | None = None,
) -> ReviewReport:
    """Assemble a ReviewReport with summary and net fragments."""
    resolved_findings = findings if findings is not None else run_rules(design)
    ops = list(operations or [])
    after = after_design
    extra_meta: dict[str, Any] = {"rule_pack": "v0", "source": "deterministic"}
    if ops and after is None:
        after = apply_operations(design, ops)
        extra_meta["semantic_diff"] = semantic_diff(design, after)
    if metadata:
        extra_meta.update(metadata)

    return ReviewReport(
        design_id=design.id,
        design_revision=design.revision,
        findings=resolved_findings,
        operations=ops,
        net_fragments=collect_net_fragments(design, resolved_findings, after=after),
        summary=summarize_findings(resolved_findings),
        metadata=extra_meta,
    )
