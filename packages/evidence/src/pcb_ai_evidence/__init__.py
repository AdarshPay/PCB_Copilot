"""Evidence store for curated facts, datasheet citations, and rule evidence."""

from pcb_ai_evidence.catalog import RULE_EVIDENCE, all_seed_refs, normalize_rule_id
from pcb_ai_evidence.seed import load_refs_from_json, seed_store, write_builtin_seed_json
from pcb_ai_evidence.service import (
    EvidenceService,
    attach_to_findings,
    default_store,
    resolve,
)
from pcb_ai_evidence.store import EvidenceStore, InMemoryEvidenceStore

__all__ = [
    "EvidenceStore",
    "InMemoryEvidenceStore",
    "EvidenceService",
    "RULE_EVIDENCE",
    "all_seed_refs",
    "normalize_rule_id",
    "seed_store",
    "load_refs_from_json",
    "write_builtin_seed_json",
    "resolve",
    "attach_to_findings",
    "default_store",
]
