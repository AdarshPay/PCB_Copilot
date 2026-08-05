"""Engineer approval/rejection telemetry for remediation proposals.

Offline-first: InMemory store for tests; optional JSONL append store for local
persistence. No external analytics. Postgres can replace the store later.
"""

from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class DecisionKind(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class DecisionRecord(BaseModel):
    """One human approve/reject decision against a remediation proposal."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    proposal_id: str
    design_id: str
    decision: DecisionKind
    reason: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    operation_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    id: str = Field(default_factory=lambda: str(uuid4()))


class ProposalSnapshot(BaseModel):
    """Lightweight context registered when a proposal is created."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    proposal_id: str
    design_id: str
    operation_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DecisionStore(ABC):
    @abstractmethod
    def append(self, record: DecisionRecord) -> DecisionRecord: ...

    @abstractmethod
    def list_recent(self, *, limit: int = 50) -> list[DecisionRecord]: ...

    @abstractmethod
    def list_for_proposal(self, proposal_id: str) -> list[DecisionRecord]: ...


class InMemoryDecisionStore(DecisionStore):
    """Thread-safe in-memory decision log (default for tests)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[DecisionRecord] = []

    def append(self, record: DecisionRecord) -> DecisionRecord:
        with self._lock:
            self._records.append(record)
            return record

    def list_recent(self, *, limit: int = 50) -> list[DecisionRecord]:
        if limit < 1:
            return []
        with self._lock:
            return list(self._records[-limit:])

    def list_for_proposal(self, proposal_id: str) -> list[DecisionRecord]:
        with self._lock:
            return [r for r in self._records if r.proposal_id == proposal_id]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


class JsonlDecisionStore(DecisionStore):
    """Append-only JSONL file store with an in-memory index for reads."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._records: list[DecisionRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        loaded: list[DecisionRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            loaded.append(DecisionRecord.model_validate(json.loads(line)))
        self._records = loaded

    def append(self, record: DecisionRecord) -> DecisionRecord:
        line = record.model_dump_json() + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
            self._records.append(record)
            return record

    def list_recent(self, *, limit: int = 50) -> list[DecisionRecord]:
        if limit < 1:
            return []
        with self._lock:
            return list(self._records[-limit:])

    def list_for_proposal(self, proposal_id: str) -> list[DecisionRecord]:
        with self._lock:
            return [r for r in self._records if r.proposal_id == proposal_id]


class DecisionTelemetry:
    """Register proposals and record engineer approve/reject decisions."""

    def __init__(self, store: DecisionStore | None = None) -> None:
        self.store: DecisionStore = store or InMemoryDecisionStore()
        self._lock = threading.Lock()
        self._proposals: dict[str, ProposalSnapshot] = {}

    def register_proposal(
        self,
        *,
        design_id: str,
        operation_ids: list[str] | None = None,
        rule_ids: list[str] | None = None,
        proposal_id: str | None = None,
    ) -> ProposalSnapshot:
        snapshot = ProposalSnapshot(
            proposal_id=proposal_id or str(uuid4()),
            design_id=design_id,
            operation_ids=list(operation_ids or []),
            rule_ids=sorted(set(rule_ids or [])),
        )
        with self._lock:
            self._proposals[snapshot.proposal_id] = snapshot
        return snapshot

    def get_proposal(self, proposal_id: str) -> ProposalSnapshot | None:
        with self._lock:
            return self._proposals.get(proposal_id)

    def record_decision(
        self,
        *,
        proposal_id: str,
        decision: DecisionKind | Literal["approve", "reject"],
        reason: str | None = None,
        design_id: str | None = None,
        operation_ids: list[str] | None = None,
        rule_ids: list[str] | None = None,
    ) -> DecisionRecord:
        kind = DecisionKind(decision)
        snapshot = self.get_proposal(proposal_id)

        resolved_design = design_id or (snapshot.design_id if snapshot else None)
        if not resolved_design:
            raise ValueError(
                f"design_id required when proposal {proposal_id!r} is not registered"
            )

        record = DecisionRecord(
            proposal_id=proposal_id,
            design_id=resolved_design,
            decision=kind,
            reason=reason,
            operation_ids=(
                list(operation_ids)
                if operation_ids is not None
                else (list(snapshot.operation_ids) if snapshot else [])
            ),
            rule_ids=(
                sorted(set(rule_ids))
                if rule_ids is not None
                else (list(snapshot.rule_ids) if snapshot else [])
            ),
        )
        return self.store.append(record)

    def list_recent(self, *, limit: int = 50) -> list[DecisionRecord]:
        return self.store.list_recent(limit=limit)

    def list_for_proposal(self, proposal_id: str) -> list[DecisionRecord]:
        return self.store.list_for_proposal(proposal_id)


def make_decision_store(path: str | Path | None = None) -> DecisionStore:
    """Build InMemory store, or JSONL store when ``path`` is set."""
    if path:
        return JsonlDecisionStore(path)
    return InMemoryDecisionStore()
