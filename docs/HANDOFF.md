# Agent handoff — PCB Copilot

Date: 2026-08-08  
Repo: https://github.com/AdarshPay/PCB_Copilot  
Branch: `main`  
Plan of record: `pcb_ai_implementation_plan_v0.md` (v0.2)  
Phase B detail: `docs/phase-b.md`

## Read this first (60-second briefing)

**Product north star:** coding-agent workflow for hardware — intent → tools → checks → approvable CAD diff (schematic now; board layout next; prompt-to-CAD later).

**Where we stopped:** Phase A is effectively complete. Phase B (AI layout) foundation was started then **paused** so a new agent can resume cleanly. Do **not** jump to Phase C prompt-to-CAD until Phase B’s KiCad-open place/route loop works.

**Your next job:** Resume Phase B from `docs/phase-b.md` — productize place/route, wire `/v1/layout`, temp board branch, KiCad action plugin, then layout benchmarks.

## Product phases

| Phase | Goal | Status |
|-------|------|--------|
| **A — Verification** | Ingest sch → Circuit IR → rules/ERC → report → typed remediations → temp `.kicad_sch` + approve telemetry | **Done** (gates met) |
| **B — AI layout** | Board IR → place/route → temp `.kicad_pcb` → DRC → KiCad plugin approve/reload | **Foundation only** (paused) |
| **C — Prompt-to-CAD** | NL → schematic + first-pass layout via same verify loop | Not started |

## Sprint status (Phase A)

| Item | Status | Notes |
|------|--------|-------|
| Foundations / Circuit IR | Done | Monorepo, schemas, golden fixtures |
| KiCad sch ingest / round-trip | Done | Hierarchy, shared-sheet, buses; emit connectivity-faithful |
| ERC | Done | Parse + runner (local/Docker/offline fixture) |
| RULE_PACK_V0 | Done | **10** deterministic checks |
| Review JSON/HTML + CI | Done | `ci_check` + `.github/workflows/ci.yml` |
| Benchmark scale | Done | **10 clean / 111 cases** |
| Component profiles | Done | **30** curated MPNs |
| Evidence | Foundation | Seed catalog + `attach_evidence` |
| Remediations / temp sch branch | Done | Planner default **off**; no production CAD writes |
| Approval telemetry | Done | `/v1/proposals/{id}/decision`, `/v1/decisions` |
| Phase B foundation | Started (paused) | See below |

## Phase B — paused state (resume here)

Full plan: Cursor plan **Phase B AI Layout** + `docs/phase-b.md` + plan §11 Day 90.

| Workstream | Status | Location |
|------------|--------|----------|
| B0 Board IR + layout skeleton | **Done** | `packages/pcb-ir`, `packages/layout` |
| B1 PCB ingest/emit + sch→board skeleton | **Done** | `pcb.py`, `board_bridge.py` |
| B2 DRC parse/runner | **Partial** | `drc_parse.py`, `drc_runner.py`; fixture `tests/fixtures/kicad/boards/rc_divider_drc.json` |
| B3 Grid place/route | **WIP** | `GridLayoutBackend` exists; not productized / no `/v1/layout` yet |
| B4 Temp board branch | **Stub** | `temp_board.py` — import explicitly; not in package `__init__` |
| B5 KiCad action plugin | **Not started** | `apps/kicad-plugin/` is README stub only |
| B6 Layout benchmarks + E2E demo | **Not started** | — |

### Phase B MVP outcome (when finished)

With KiCad open on a small 2-layer project: plugin → API layouts board into temp `.kicad_pcb` → DRC gate → human approve → reload sidecar board. Constraints: ≤~20 footprints, own grid placer + 2-layer maze router, no production overwrite.

### Resume checklist (ordered)

1. Productize `GridLayoutBackend` + `python -m pcb_ai_layout layout …` + `POST /v1/layout`
2. Wire offline DRC into CI; optional live `kicad-cli pcb drc`
3. Re-export `compile_temp_board_branch`; hook layout proposals into decision telemetry
4. KiCad 10 action plugin → local API → approve/reload
5. Layout benchmarks + Phase B gate checklist in this handoff before Phase C

## Architecture (current)

```text
.kicad_sch → kicad-adapter → Circuit IR
                ↓
     RULE_PACK_V0 + optional ERC (+ attach_evidence)
                ↓
     ReviewReport (JSON/HTML)
                ↓
     typed Operations (deterministic; planner default off)
                ↓
     apply_operations / compile_temp_branch → temp .kicad_sch
                ↓
     DecisionRecord approve/reject

Phase B (partial):
  Circuit IR → schematic_design_to_board_skeleton → Board IR
            → GridLayoutBackend (WIP) → write_pcb → .kicad_pcb
            → parse_drc_report / run_board_drc (offline OK)
```

## Non-negotiables

1. Circuit IR is the electrical source of truth; Board IR for placement/copper.
2. Deterministic tools own syntax / graph / rules / (later) DRC.
3. Human approval for CAD changes; **never** mutate production files from the agent.
4. Branch-only / temp-dir artifacts; `production_mutation: false`.
5. KiCad 10 via file parse + `kicad-cli` (not deprecated SWIG).
6. Keep ERC/DRC/SPICE success from being treated as product-level correctness.

## Repo map

```text
apps/api/                 /health, /v1/reviews, /ingest, /proposals, /temp-branch, /decisions
apps/web/                 Stub
apps/kicad-plugin/        Stub README only — Phase B plugin goes here
packages/circuit-ir/      Design, Component, Pin, Net, Finding, Operation, ReviewReport
packages/pcb-ir/          Board, FootprintInstance, Track, Via, Outline, … (Phase B)
packages/kicad-adapter/   sch + pcb ingest/emit, hierarchy, board_bridge
packages/verification/    RULE_PACK_V0, ERC, DRC parse/runner, reports
packages/layout/          LayoutPlanner, NullLayoutBackend, GridLayoutBackend WIP, run_layout_job
packages/transactions/    apply_operations, compile_temp_branch; temp_board.py (explicit import)
packages/agent/           remediations, Planner(default off), DecisionTelemetry
packages/component-library/  30 profiles + registry
packages/evidence/        EvidenceService + seed catalog
packages/benchmarks/      first-pack + ci_check
services/worker/          verify_design, run_erc (run_drc not wired yet)
infra/docker/kicad-cli/   KiCad 10 CLI image
tests/fixtures/golden/    10 clean IR + output_conflict
tests/fixtures/kicad/     sch fixtures + boards/ DRC JSON
```

## What works today (Phase A)

- Full sch ingest → IR → 10 rules → ERC fixture → JSON/HTML report
- Hierarchy / shared-sheet / bus ingest; connectivity-faithful sch emit
- 30 component profiles; evidence attach hook
- Deterministic remediations; `POST /v1/proposals`; `compile_temp_branch`; decision telemetry
- Benchmark **111/111**; CI offline hardware check

## Phase B already on disk (do not redo)

- `packages/pcb-ir` — Board IR models + `LAYOUT_OPERATION_TYPES`
- `packages/layout` — `backend.py`, `grid_backend.py`, `service.py`, `__main__.py`
- `packages/kicad-adapter/pcb.py` — `ingest_pcb` / `write_pcb` / emit AST
- `packages/kicad-adapter/board_bridge.py` — `schematic_design_to_board_skeleton`
- `packages/verification/drc_*.py` — offline DRC JSON → Finding (`source=kicad_drc`)
- `packages/transactions/temp_board.py` — `compile_temp_board_branch` (needs layout installed)
- `tests/test_pcb_ir_foundation.py` — foundation smoke tests
- `scripts/install_dev.ps1` — installs `pcb-ir` then `layout`

## How to run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\install_dev.ps1
pytest
```

Smoke:

```powershell
python -m pcb_ai_kicad_adapter tests/fixtures/kicad/rc_divider.kicad_sch --report --html reports/rc_divider.html -o reports/rc_divider.json
python -m pcb_ai_benchmarks -o reports/run-manifest.json
python -m pcb_ai_benchmarks.ci_check -o reports/ci-hardware-check.json
```

Optional API:

```powershell
uvicorn pcb_ai_api.main:app --reload --app-dir apps/api/src
```

Notes:
- Windows Cursor shells often need unrestricted permissions if sandbox is unavailable.
- Python 3.12+ (dev has also used 3.14).
- Keep paths offline-testable (Docker KiCad optional).

## Tests

Expect **~235 passed** (`pytest`) including `test_pcb_ir_foundation.py`.  
Benchmark: **111** first-pack cases.  
`ci_check` exit **0** with offline ERC fixture.

## Remaining gaps (known)

**Phase A residuals (non-blocking):** lossless multi-file sch emit; deeper bus aliases; deep datasheet RAG.

**Phase B remaining:** productize layout API/CLI; CI DRC; temp board branch UX; **KiCad plugin**; benchmarks; KiCad-open E2E demo.

**Not built:** React review UI; production LLM planner; ngspice; Altium; Phase C.

## Guardrails for the next agent

- Prefer small, test-backed diffs.
- Do not enable LLM CAD mutation of production files.
- Do not start Phase C until Phase B plugin demo + DRC-gated layout benchmarks exist.
- Commit only when the user asks; never force-push `main`.
- Read `pcb_ai_implementation_plan_v0.md` (v0.2) and `docs/phase-b.md` before changing direction.

## Key entry files

| Concern | Start here |
|---------|------------|
| Handoff / Phase B status | `docs/HANDOFF.md`, `docs/phase-b.md` |
| Plan | `pcb_ai_implementation_plan_v0.md` |
| Circuit IR | `packages/circuit-ir/src/pcb_ai_circuit_ir/models.py` |
| Board IR | `packages/pcb-ir/src/pcb_ai_pcb_ir/models.py` |
| Layout WIP | `packages/layout/src/pcb_ai_layout/grid_backend.py`, `service.py` |
| PCB I/O | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/pcb.py`, `board_bridge.py` |
| Rules / ERC / DRC | `packages/verification/src/pcb_ai_verification/` |
| Temp sch branch | `packages/transactions/src/pcb_ai_transactions/temp_branch.py` |
| Temp board stub | `packages/transactions/src/pcb_ai_transactions/temp_board.py` |
| Plugin stub | `apps/kicad-plugin/README.md` |
| API | `apps/api/src/pcb_ai_api/` |
