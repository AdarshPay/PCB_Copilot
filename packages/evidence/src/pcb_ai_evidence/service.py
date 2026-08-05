"""High-level datasheet / evidence service (offline curated catalog)."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_circuit_ir.models import EvidenceRef, Finding

from pcb_ai_evidence.seed import seed_store
from pcb_ai_evidence.store import EvidenceStore, InMemoryEvidenceStore


class EvidenceService:
    """Facade: resolve / attach / search / list over a seeded EvidenceStore."""

    def __init__(self, store: EvidenceStore | None = None) -> None:
        self.store: EvidenceStore = store if store is not None else seed_store()

    @classmethod
    def with_defaults(cls) -> EvidenceService:
        return cls(seed_store())

    @classmethod
    def from_json(cls, path: str | Path, *, include_builtin: bool = True) -> EvidenceService:
        return cls(seed_store(json_path=path, include_builtin=include_builtin))

    def resolve(self, rule_id: str) -> list[EvidenceRef]:
        return self.store.resolve(rule_id)

    def attach_to_findings(self, findings: list[Finding]) -> list[Finding]:
        return self.store.attach_to_findings(findings)

    def search(
        self,
        *,
        query: str | None = None,
        kind: str | None = None,
        rule_id: str | None = None,
    ) -> list[EvidenceRef]:
        return self.store.search(query=query, kind=kind, rule_id=rule_id)

    def list(self) -> list[EvidenceRef]:
        return self.store.list()

    def get(self, evidence_id: str) -> EvidenceRef | None:
        return self.store.get(evidence_id)

    def upsert(self, ref: EvidenceRef) -> None:
        self.store.upsert(ref)


def resolve(rule_id: str, *, store: EvidenceStore | None = None) -> list[EvidenceRef]:
    """Module-level helper: resolve evidence for a rule_id."""
    svc = EvidenceService(store) if store is not None else EvidenceService.with_defaults()
    return svc.resolve(rule_id)


def attach_to_findings(
    findings: list[Finding],
    *,
    store: EvidenceStore | None = None,
) -> list[Finding]:
    """Module-level helper: enrich findings with curated evidence_refs."""
    svc = EvidenceService(store) if store is not None else EvidenceService.with_defaults()
    return svc.attach_to_findings(findings)


def default_store() -> InMemoryEvidenceStore:
    """Return a freshly seeded in-memory store."""
    store = seed_store()
    assert isinstance(store, InMemoryEvidenceStore)
    return store
