# Phase B — AI layout / redraw

**Handoff:** `docs/HANDOFF.md`  
**Plan:** `pcb_ai_implementation_plan_v0.md` §11 Day 90+ and Cursor plan **Phase B AI Layout**

## Status (stopping point — 2026-08-08)

**Foundation started; full KiCad-open place/route loop not finished.** Phase A remains green (~235 pytest). Resume here rather than redoing B0/B1.

| Workstream | Status |
|------------|--------|
| B0 Board IR + layout package skeleton | **Done** (`packages/pcb-ir`, `packages/layout`) |
| B1 PCB ingest/emit + schematic→board skeleton | **Done** (`pcb.py`, `board_bridge.py`) |
| B2 DRC parse/runner (offline) | **Partial** — modules + `rc_divider_drc.json`; CI/plugin later |
| B3 Grid place/route | **WIP** (`GridLayoutBackend`, `run_layout_job`, `__main__.py`) — not API-wired |
| B4 Temp board branch | **Stub** (`temp_board.py`, explicit import only) |
| B5 KiCad action plugin | **Not started** |
| B6 Layout benchmarks + E2E demo | **Not started** |

## Resume next (do in order)

1. Productize `GridLayoutBackend` + `python -m pcb_ai_layout layout <source> --out DIR` + `POST /v1/layout`
2. Wire offline DRC into CI; optional live `kicad-cli pcb drc`
3. Re-export `compile_temp_board_branch`; register layout proposals with decision telemetry
4. KiCad 10 action plugin → local API → approve/reload sidecar `*-copilot.kicad_pcb`
5. Layout benchmarks + Phase B gate checklist in HANDOFF before Phase C

## MVP outcome (when complete)

With KiCad open: run plugin → service places/routes a small 2-layer board into a
temp `.kicad_pcb` → DRC gate → human approve → reload. No production overwrite.

MVP constraints: ≤~20 footprints; own grid placer + 2-layer A*/maze router; connectivity-faithful PCB emit; human approval always.
