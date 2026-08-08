"""Deterministic verification rule engine."""

from pcb_ai_verification.drc_parse import normalize_drc_json, parse_drc_report
from pcb_ai_verification.drc_runner import DrcRunnerError, DrcRunResult, run_board_drc
from pcb_ai_verification.engine import RuleEngine, run_rules
from pcb_ai_verification.erc_map import attach_design_objects, collect_objects_from_items
from pcb_ai_verification.erc_parse import normalize_erc_json, normalize_erc_text, parse_erc_report
from pcb_ai_verification.erc_runner import ErcRunnerError, ErcRunResult, run_schematic_erc
from pcb_ai_verification.evidence import attach_evidence
from pcb_ai_verification.html_report import render_html_report
from pcb_ai_verification.report import build_review_report, collect_net_fragments, summarize_findings
from pcb_ai_verification.rules import RULE_PACK_V0

__all__ = [
    "RuleEngine",
    "run_rules",
    "RULE_PACK_V0",
    "attach_evidence",
    "parse_erc_report",
    "normalize_erc_json",
    "normalize_erc_text",
    "collect_objects_from_items",
    "attach_design_objects",
    "run_schematic_erc",
    "ErcRunResult",
    "ErcRunnerError",
    "parse_drc_report",
    "normalize_drc_json",
    "run_board_drc",
    "DrcRunResult",
    "DrcRunnerError",
    "build_review_report",
    "collect_net_fragments",
    "summarize_findings",
    "render_html_report",
]
