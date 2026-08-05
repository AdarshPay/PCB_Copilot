"""In-memory evidence store for the prototype."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pcb_ai_circuit_ir.models import EvidenceRef, Finding

from pcb_ai_evidence.catalog import (
    RELATED_BY_RULE,
    RULE_EVIDENCE,
    normalize_rule_id,
    rule_evidence_id,
)


class EvidenceStore(ABC):
    @abstractmethod
    def get(self, evidence_id: str) -> EvidenceRef | None: ...

    @abstractmethod
    def upsert(self, ref: EvidenceRef) -> None: ...

    @abstractmethod
    def list(self) -> list[EvidenceRef]: ...

    def search(
        self,
        *,
        query: str | None = None,
        kind: str | None = None,
        rule_id: str | None = None,
    ) -> list[EvidenceRef]:
        """Filter listed refs by optional substring query, kind, and/or rule linkage."""
        q = query.lower().strip() if query else None
        kind_filter = kind.lower().strip() if kind else None
        bare_rule = normalize_rule_id(rule_id) if rule_id else None
        rule_eid = rule_evidence_id(bare_rule) if bare_rule else None

        results: list[EvidenceRef] = []
        for ref in self.list():
            if kind_filter and ref.kind.lower() != kind_filter:
                continue
            if bare_rule is not None:
                related_ids = {r.id for r in RELATED_BY_RULE.get(bare_rule, [])}
                if ref.id != rule_eid and ref.id not in related_ids:
                    # Also match refs whose id embeds the rule id (e.g. rule:...)
                    if bare_rule not in ref.id and (ref.uri or "").find(bare_rule) < 0:
                        continue
            if q:
                haystack = " ".join(
                    filter(
                        None,
                        [
                            ref.id,
                            ref.kind,
                            ref.title or "",
                            ref.uri or "",
                            ref.excerpt or "",
                        ],
                    )
                ).lower()
                if q not in haystack:
                    continue
            results.append(ref)
        return results

    def resolve(self, rule_id: str) -> list[EvidenceRef]:
        """Return curated evidence for a rule_id (primary rule ref + related)."""
        bare = normalize_rule_id(rule_id)
        ordered: list[EvidenceRef] = []
        seen: set[str] = set()

        primary_id = rule_evidence_id(bare)
        primary = self.get(primary_id)
        if primary is None and bare in RULE_EVIDENCE:
            primary = RULE_EVIDENCE[bare]
        if primary is not None:
            ordered.append(primary)
            seen.add(primary.id)

        for ref in RELATED_BY_RULE.get(bare, []):
            curated = self.get(ref.id) or ref
            if curated.id not in seen:
                ordered.append(curated)
                seen.add(curated.id)

        # Any additional store hits tagged to this rule
        for ref in self.search(rule_id=bare):
            if ref.id not in seen:
                ordered.append(ref)
                seen.add(ref.id)
        return ordered

    def attach_to_findings(self, findings: list[Finding]) -> list[Finding]:
        """Return findings with evidence_refs enriched from the catalog.

        Existing refs keep their ids; missing title/uri/excerpt/confidence are filled
        from the store. Related curated evidence for the finding's rule_id is appended
        when not already present.
        """
        enriched: list[Finding] = []
        for finding in findings:
            by_id: dict[str, EvidenceRef] = {}
            for ref in finding.evidence_refs:
                by_id[ref.id] = _merge_ref(ref, self.get(ref.id))

            for curated in self.resolve(finding.rule_id):
                if curated.id in by_id:
                    by_id[curated.id] = _merge_ref(by_id[curated.id], curated)
                else:
                    by_id[curated.id] = curated

            # Preserve original order, then append newly added related refs
            ordered_ids = [r.id for r in finding.evidence_refs]
            for eid in by_id:
                if eid not in ordered_ids:
                    ordered_ids.append(eid)

            enriched.append(
                finding.model_copy(
                    update={"evidence_refs": [by_id[eid] for eid in ordered_ids if eid in by_id]}
                )
            )
        return enriched


def _merge_ref(base: EvidenceRef, overlay: EvidenceRef | None) -> EvidenceRef:
    """Fill empty fields on base from overlay without wiping explicit base values."""
    if overlay is None:
        return base
    return EvidenceRef(
        id=base.id,
        kind=base.kind or overlay.kind,
        title=base.title or overlay.title,
        uri=base.uri or overlay.uri,
        page=base.page if base.page is not None else overlay.page,
        excerpt=base.excerpt or overlay.excerpt,
        confidence=(
            overlay.confidence
            if (base.excerpt is None and overlay.excerpt is not None)
            else base.confidence
        ),
    )


class InMemoryEvidenceStore(EvidenceStore):
    def __init__(self) -> None:
        self._items: dict[str, EvidenceRef] = {}

    def get(self, evidence_id: str) -> EvidenceRef | None:
        return self._items.get(evidence_id)

    def upsert(self, ref: EvidenceRef) -> None:
        self._items[ref.id] = ref

    def list(self) -> list[EvidenceRef]:
        return list(self._items.values())
