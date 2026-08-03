# Round-trip tests (KiCad AST ↔ IR ↔ KiCad)

See `tests/test_roundtrip_kicad.py` and fixtures under `tests/fixtures/kicad/`.

Coverage:
- Lossless AST parse → serialize → parse
- `.kicad_sch` → Circuit IR (components, pins, labels, nets)
- IR → emit schematic → IR with no semantic change
- CLI: `python -m pcb_ai_kicad_adapter path.kicad_sch --rules`
