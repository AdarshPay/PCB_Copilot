"""Load curated EvidenceRef catalogs from JSON (offline only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pcb_ai_circuit_ir.models import EvidenceRef

from pcb_ai_evidence.catalog import all_seed_refs
from pcb_ai_evidence.store import EvidenceStore, InMemoryEvidenceStore


def evidence_ref_from_mapping(data: dict[str, Any]) -> EvidenceRef:
    return EvidenceRef.model_validate(data)


def load_refs_from_json(path: str | Path) -> list[EvidenceRef]:
    """Parse a JSON file containing a list or ``{\"items\": [...]}`` of EvidenceRef dicts."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("Seed JSON must be a list or an object with an 'items' list.")
    return [evidence_ref_from_mapping(item) for item in items]


def default_seed_json_path() -> Path:
    """Packaged seed file under ``pcb_ai_evidence/data/seed_catalog.json``."""
    return Path(__file__).resolve().parent / "data" / "seed_catalog.json"


def load_packaged_seed_refs() -> list[EvidenceRef]:
    path = default_seed_json_path()
    if path.is_file():
        return load_refs_from_json(path)
    return all_seed_refs()


def seed_store(
    store: EvidenceStore | None = None,
    *,
    refs: Iterable[EvidenceRef] | None = None,
    json_path: str | Path | None = None,
    include_builtin: bool = True,
) -> EvidenceStore:
    """Populate a store from builtin catalog and/or a JSON seed file.

    Later upserts win on id collisions (JSON overrides builtin when both are used).
    """
    target: EvidenceStore = store if store is not None else InMemoryEvidenceStore()
    if include_builtin:
        for ref in all_seed_refs():
            target.upsert(ref)
    if json_path is not None:
        for ref in load_refs_from_json(json_path):
            target.upsert(ref)
    elif refs is None and include_builtin:
        packaged = default_seed_json_path()
        if packaged.is_file():
            for ref in load_refs_from_json(packaged):
                target.upsert(ref)
    if refs is not None:
        for ref in refs:
            target.upsert(ref)
    return target


def write_builtin_seed_json(path: str | Path | None = None) -> Path:
    """Write the in-code catalog to JSON (helper for regenerating the packaged seed)."""
    out = Path(path) if path is not None else default_seed_json_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "description": "Offline curated evidence catalog (rules + datasheet/profile placeholders).",
        "items": [ref.model_dump(mode="json") for ref in all_seed_refs()],
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
