# Architecture notes

See `pcb_ai_implementation_plan_v0.md` at the repository root for the product decision,
Phase A MVP architecture, Circuit IR, rule pack, and foundations → layout → prompt-to-CAD timeline.

## Source of truth

1. Circuit IR for AI reasoning
2. Deterministic tools for syntax, graph integrity, and rule compliance (later: DRC/constraints for layout)
3. Human approval for electrical and layout changes that affect production CAD
4. Branch-only reversible patches — never direct production CAD mutation by the LLM
5. North star: coding-agent loop for hardware; Phase B layout then Phase C prompt-to-CAD after Phase A gates

## Native verification (KiCad ERC)

- Image: `infra/docker/kicad-cli/` (wraps official `kicad/kicad`)
- Parser / mapper: `pcb_ai_verification.erc_parse` / `erc_map` → `Finding` with `source="kicad_erc"`
- Runner: `pcb_ai_verification.erc_runner.run_schematic_erc` (local CLI, Docker, or fixture/mock)
- Worker job: `type: "run_erc"` in `pcb_ai_worker`

## KiCad hierarchy / UUID round-trip (Phase A research)

- Ingest walks `(sheet …)` / `Sheetfile` children and sets `SourceLocation.sheet` to KiCad-style paths (`/`, `/{sheet-uuid}`, …).
- The same Sheetfile may be instantiated multiple times (distinct sheet UUIDs / paths); per-path `(instances … (reference …))` selects designators.
- Connectivity merges global/power labels across sheets and bridges parent sheet pins to child `hierarchical_label`s by name.
- Buses: `(bus)` / `(bus_entry)` stay on a separate connectivity graph from wires; vector/group labels expand to members (`bus_members` / `bus` constraints). Members are not shorted together.
- AST serialize preserves UUID atoms; `uuid_fingerprint` / `uuid_equal` assert component UUID survival through emit.
- Emit is connectivity-faithful with partial sheet-path / coordinate preservation — not a lossless multi-file hierarchy writer (see `tests/roundtrip/README.md`).

## Phase B layout (in progress / paused)

- Board IR: `packages/pcb-ir`
- Layout package: `packages/layout` (`NullLayoutBackend`, `GridLayoutBackend` WIP)
- PCB adapter: `ingest_pcb` / `write_pcb` / `schematic_design_to_board_skeleton`
- DRC: `parse_drc_report` / `run_board_drc` (offline fixture path)
- Status and resume checklist: `docs/phase-b.md`

