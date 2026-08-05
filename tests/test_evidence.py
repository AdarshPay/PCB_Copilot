"""Evidence store and finding enrichment tests (offline catalog)."""

from __future__ import annotations

import json
from pathlib import Path

from pcb_ai_circuit_ir.models import EvidenceRef, Finding, Severity
from pcb_ai_evidence import (
    EvidenceService,
    InMemoryEvidenceStore,
    RULE_EVIDENCE,
    attach_to_findings,
    resolve,
    seed_store,
    write_builtin_seed_json,
)
from pcb_ai_evidence.catalog import all_seed_refs
from pcb_ai_evidence.seed import load_refs_from_json
from pcb_ai_verification import RULE_PACK_V0, attach_evidence, run_rules
from tests.conftest import load_golden


def test_builtin_catalog_covers_rule_pack() -> None:
    pack_ids = {rule_id for rule_id, _ in RULE_PACK_V0}
    assert set(RULE_EVIDENCE) == pack_ids
    store = seed_store()
    for rule_id in pack_ids:
        refs = store.resolve(rule_id)
        assert refs, f"expected evidence for {rule_id}"
        assert refs[0].id == f"rule:{rule_id}"
        assert refs[0].excerpt
        assert refs[0].uri


def test_resolve_accepts_rule_prefix() -> None:
    a = resolve("elec.open_drain_pullup")
    b = resolve("rule:elec.open_drain_pullup")
    assert [r.id for r in a] == [r.id for r in b]
    kinds = {r.kind for r in a}
    assert "rule" in kinds
    assert "datasheet" in kinds or "note" in kinds


def test_search_and_list() -> None:
    svc = EvidenceService.with_defaults()
    listed = svc.list()
    assert len(listed) >= len(RULE_EVIDENCE)

    datasheets = svc.search(kind="datasheet")
    assert datasheets
    assert all(r.kind == "datasheet" for r in datasheets)

    pullup = svc.search(query="pull-up")
    assert any("open_drain" in r.id or "pullup" in r.id.lower() or "pull-up" in (r.excerpt or "").lower() for r in pullup)

    by_rule = svc.search(rule_id="elec.power_source")
    assert any(r.id == "rule:elec.power_source" for r in by_rule)
    assert any(r.kind == "datasheet" for r in by_rule)


def test_attach_to_findings_enriches_stub_refs() -> None:
    finding = Finding(
        rule_id="elec.output_conflict",
        severity=Severity.ERROR,
        objects=["NET"],
        explanation="conflict",
        evidence_refs=[
            EvidenceRef(
                id="rule:elec.output_conflict",
                kind="rule",
                title="Output-to-output conflicts",
            )
        ],
    )
    enriched = attach_to_findings([finding])[0]
    primary = next(r for r in enriched.evidence_refs if r.id == "rule:elec.output_conflict")
    assert primary.uri == "pcb-ai://rules/elec.output_conflict"
    assert primary.excerpt
    assert "multiple" in primary.excerpt.lower() or "output" in primary.excerpt.lower()


def test_attach_appends_related_evidence() -> None:
    finding = Finding(
        rule_id="elec.open_drain_pullup",
        severity=Severity.ERROR,
        objects=["SDA"],
        explanation="missing pull-up",
        evidence_refs=[
            EvidenceRef(id="rule:elec.open_drain_pullup", kind="rule", title="pull-up")
        ],
    )
    enriched = attach_to_findings([finding])[0]
    ids = [r.id for r in enriched.evidence_refs]
    assert ids[0] == "rule:elec.open_drain_pullup"
    assert "datasheet:TMP117" in ids or "note:i2c_pullup_practice" in ids


def test_json_seed_loader(tmp_path: Path) -> None:
    path = tmp_path / "seed.json"
    write_builtin_seed_json(path)
    loaded = load_refs_from_json(path)
    assert len(loaded) == len(all_seed_refs())

    store = InMemoryEvidenceStore()
    seed_store(store, json_path=path, include_builtin=False)
    assert store.get("rule:struct.unique_references") is not None

    # Overlay override
    override = tmp_path / "override.json"
    override.write_text(
        json.dumps(
            [
                {
                    "id": "rule:struct.unique_references",
                    "kind": "rule",
                    "title": "Unique references (override)",
                    "uri": "pcb-ai://rules/struct.unique_references",
                    "excerpt": "Override excerpt from JSON seed.",
                    "confidence": 0.5,
                }
            ]
        ),
        encoding="utf-8",
    )
    svc = EvidenceService.from_json(override, include_builtin=True)
    ref = svc.get("rule:struct.unique_references")
    assert ref is not None
    assert ref.excerpt == "Override excerpt from JSON seed."
    assert ref.confidence == 0.5


def test_packaged_seed_json_exists() -> None:
    from pcb_ai_evidence.seed import default_seed_json_path

    path = default_seed_json_path()
    assert path.is_file(), f"missing packaged seed at {path}"
    refs = load_refs_from_json(path)
    assert {r.id for r in refs} >= {f"rule:{rid}" for rid in RULE_EVIDENCE}


def test_verification_attach_evidence_helper() -> None:
    design = load_golden("output_conflict.json")
    findings = run_rules(design)
    assert any(f.rule_id == "elec.output_conflict" for f in findings)
    enriched = attach_evidence(findings)
    conflict = next(f for f in enriched if f.rule_id == "elec.output_conflict")
    primary = conflict.evidence_refs[0]
    assert primary.uri
    assert primary.excerpt
