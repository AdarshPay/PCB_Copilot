"""Rule engine orchestration."""

from __future__ import annotations

from pcb_ai_circuit_ir.models import Design, Finding
from pcb_ai_verification.rules import RULE_PACK_V0, RuleFn


class RuleEngine:
    def __init__(self, rules: list[tuple[str, RuleFn]] | None = None) -> None:
        self.rules = rules if rules is not None else list(RULE_PACK_V0)

    def run(self, design: Design) -> list[Finding]:
        findings: list[Finding] = []
        for _rule_id, fn in self.rules:
            findings.extend(fn(design))
        return findings


def run_rules(design: Design) -> list[Finding]:
    return RuleEngine().run(design)
