"""In-memory evidence store for the prototype."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pcb_ai_circuit_ir.models import EvidenceRef


class EvidenceStore(ABC):
    @abstractmethod
    def get(self, evidence_id: str) -> EvidenceRef | None: ...

    @abstractmethod
    def upsert(self, ref: EvidenceRef) -> None: ...

    @abstractmethod
    def list(self) -> list[EvidenceRef]: ...


class InMemoryEvidenceStore(EvidenceStore):
    def __init__(self) -> None:
        self._items: dict[str, EvidenceRef] = {}

    def get(self, evidence_id: str) -> EvidenceRef | None:
        return self._items.get(evidence_id)

    def upsert(self, ref: EvidenceRef) -> None:
        self._items[ref.id] = ref

    def list(self) -> list[EvidenceRef]:
        return list(self._items.values())
