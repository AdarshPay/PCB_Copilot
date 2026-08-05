# Round-trip tests (KiCad AST ↔ IR ↔ KiCad)

See `tests/test_roundtrip_kicad.py` and fixtures under `tests/fixtures/kicad/`.

Coverage:
- Lossless AST parse → serialize → parse (exact UUID atom preservation)
- `.kicad_sch` → Circuit IR (components, pins, labels, nets, sheet paths)
- Multi-sheet hierarchy: `fixtures/kicad/hierarchy/` (root + child; sheet-pin ↔ hierarchical_label)
- Shared sheet / multi-instance: `fixtures/kicad/shared_sheet/` (same Sheetfile under two sheet UUIDs; per-path refs)
- Bus members: `fixtures/kicad/bus/` (`bus` / `bus_entry`, vector label expansion, members stay electrically separate)
- IR → emit schematic → IR with no semantic change; component UUID fingerprint equality
- Emit preserves `SourceLocation` x/y when present, writes `(instances …)` sheet paths and `(sheet_instances …)`
- CLI: `python -m pcb_ai_kicad_adapter path.kicad_sch --rules`

## Remaining limits

- Emit is still a **flat** connectivity sketch: it does **not** rewrite child `.kicad_sch` files, `(sheet …)` symbols, or hierarchical pins/labels as a multi-file project.
- Shared-sheet CAD symbol UUIDs are qualified in IR when the same uuid appears under multiple instance paths (`attributes.cad_uuid` keeps the file uuid).
- Local nets with the same hierarchical name on different instances may share the net `name` string (distinct endpoint sets / uuids).
- Bus aliases / advanced KiCad bus naming beyond `NAME[M..N]` and `{A B}` / `PRE{A B}` are not expanded.
- Original wire/bus stroke geometry is not preserved on emit (synthetic star wires / minimal bus segments).
