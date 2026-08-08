# Phase B — AI layout / redraw

**Handoff:** `docs/HANDOFF.md`  
**Plan:** `pcb_ai_implementation_plan_v0.md` §11 Day 90+ and Cursor plan **Phase B AI Layout**

## Status (stopping point — 2026-08-08)

**B0–B5 done** (layout API/CLI, offline DRC CI, temp board branch, KiCad action plugin). **B6** (layout benchmarks + gated E2E demo checklist) remains. Phase A remains green.

| Workstream | Status |
|------------|--------|
| B0 Board IR + layout package skeleton | **Done** (`packages/pcb-ir`, `packages/layout`) |
| B1 PCB ingest/emit + schematic→board skeleton | **Done** (`pcb.py`, `board_bridge.py`) |
| B2 DRC parse/runner (offline) | **Done** — `ci_check` + workflow; live `kicad-cli` optional |
| B3 Grid place/route | **Done** — CLI `python -m pcb_ai_layout layout …`; `POST /v1/layout` (+ `/from-design`) |
| B4 Temp board branch | **Done** — `compile_temp_board_branch` lazy re-export; `POST /v1/temp-board` (+ `/from-design`); overwrite guard; decision telemetry |
| B5 KiCad action plugin | **Done** — `apps/kicad-plugin/pcb_copilot_layout/` + `scripts/install_kicad_plugin.ps1` |
| B6 Layout benchmarks + E2E demo | **Not started** |

## Resume next (do in order)

1. ~~Productize `GridLayoutBackend` + CLI + `POST /v1/layout`~~ **Done**
2. ~~Wire offline DRC into CI; optional live `kicad-cli pcb drc`~~ **Done**
3. ~~Re-export `compile_temp_board_branch`; register layout proposals with decision telemetry~~ **Done**
4. ~~KiCad 10 action plugin → local API → approve/reload sidecar `*-copilot.kicad_pcb`~~ **Done**
5. Layout benchmarks + Phase B gate checklist in HANDOFF before Phase C

## MVP outcome (when complete)

With KiCad open: run plugin → service places/routes a small 2-layer board into a
temp `.kicad_pcb` → DRC gate → human approve → reload. No production overwrite.

MVP constraints: ≤~20 footprints; own grid placer + 2-layer A*/maze router; connectivity-faithful PCB emit; human approval always.
