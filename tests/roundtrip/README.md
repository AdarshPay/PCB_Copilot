# Round-trip tests (KiCad AST ↔ IR ↔ KiCad)

See `tests/test_roundtrip_kicad.py` and fixtures under `tests/fixtures/kicad/`.

Coverage:
- Lossless AST parse → serialize → parse (exact UUID atom preservation)
- `.kicad_sch` → Circuit IR (components, pins, labels, nets, sheet paths)
- Multi-sheet hierarchy: `fixtures/kicad/hierarchy/` (root + child; sheet-pin ↔ hierarchical_label)
- IR → emit schematic → IR with no semantic change; component UUID fingerprint equality
- CLI: `python -m pcb_ai_kicad_adapter path.kicad_sch --rules`

Known gaps (research item #3): complex hierarchy (shared sheet file / multiple instances),
bus members, and lossless emit of original geometry/sheet structure (emit is connectivity-faithful).
