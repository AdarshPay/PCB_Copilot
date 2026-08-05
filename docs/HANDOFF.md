# Agent handoff — PCB Copilot

Date: 2026-08-04  
Repo: https://github.com/AdarshPay/PCB_Copilot  
Branch: `main`  
Plan of record: `pcb_ai_implementation_plan_v0.md` (v0.2)

## Product in one sentence

**North star:** coding-agent workflow for hardware (intent → tools → checks → approvable CAD diff).  
**Current MVP (Phase A):** verification-first KiCad schematic copilot — ingest → typed Circuit IR → deterministic checks (+ optional KiCad ERC) → review report → typed remediations / IR transactions (planner default off; no production CAD writes).  
**Later:** Phase B AI layout/redraw, then Phase C prompt-to-CAD — only after Phase A gates (see `pcb_ai_implementation_plan_v0.md` v0.2).

## Sprint status

| Sprint days | Status | Notes |
|-------------|--------|-------|
| 1–2 Foundations | Done | Monorepo, schemas, Docker compose, golden IR fixtures |
| 3–5 KiCad ingest | Done | Parse/normalize/round-trip `.kicad_sch` |
| 6–7 Native ERC | Done | ERC→Finding, Docker image, offline tests |
| 8–9 First rules + mutations | Done | Five first-pack rules + single-fault mutations |
| 10 Review artifact | Done | JSON + HTML report, run manifest |
| Day 30 rules | Done | 10 checks in RULE_PACK_V0 (incl. footprint presence) |
| Day 30 CI command | Done | Offline ingest + rules + ERC fixture; `.github/workflows/ci.yml` |
| Day 30 scale | Done | **10 clean / 100 mutations + conflict = 111** cases (all pass) |
| Hierarchy normalize | Mostly done | Shared-sheet multi-instance + bus members; emit still flat/connectivity-faithful |
| Component profiles | Done | **30** curated profiles + registry |
| Evidence service | Foundation done | `EvidenceService` + seed catalog + `attach_evidence` hook |
| Typed remediations / tx | Done (IR + temp emit) | Deterministic remediations, `apply_operations`, `compile_temp_branch`, `POST /v1/proposals`, `POST /v1/temp-branch` |
| Approval telemetry | Done | `DecisionRecord` + `POST /v1/proposals/{id}/decision`, `POST/GET /v1/decisions` |

**Sprint exit criterion (met):** one schematic can be ingested, normalized, checked, round-tripped, and reported **without an LLM**.

**Phase A gates:** largely met for the Day-60 agent-ready bar (scale 10/100+, profiles 30/30, temp-branch emit, telemetry, normalize progress). Residual: lossless multi-file hierarchy emit and deeper bus/geometry fidelity — acceptable as known limits, not blockers for starting Phase B.

**Next horizon:** **Phase B AI layout/redraw** (PCB IR + DRC + placement/routing agent), then Phase C prompt-to-CAD. Do **not** treat residual emit hierarchy gaps as a reason to reopen Phase A scope unless layout work depends on them.

## Architecture (source of truth)

```text
.kicad_sch → kicad-adapter (AST, hierarchy) → Circuit IR
                ↓
     verification rules + optional ERC (+ attach_evidence)
                ↓
     ReviewReport (JSON) + HTML report
                ↓
     typed Operations (deterministic remediations; planner default off)
                ↓
     apply_operations / export_branch_diff (IR copy)
                ↓
     compile_temp_branch → temporary .kicad_sch (connectivity-faithful)
                ↓
     DecisionRecord approve/reject telemetry → human promote (not auto)
```

Non-negotiables from the plan:
1. Circuit IR is the reasoning source of truth.
2. Deterministic tools own syntax / graph / rules.
3. Human approval required for electrical changes.
4. PostgreSQL (+ pgvector later); no Neo4j in MVP.
5. Target KiCad 10; use file parse + `kicad-cli`, not deprecated SWIG bindings.

## Repo map

```text
apps/api/                 FastAPI: /health, /v1/reviews, /v1/ingest/schematic, /v1/proposals, /v1/temp-branch, /v1/decisions
apps/web/                 Stub only
apps/kicad-plugin/        Stub only
packages/circuit-ir/      Design, Component, Pin, Net, Finding, Operation, ReviewReport, NetFragment
packages/kicad-adapter/   parser, connectivity, normalize (hierarchy), emit (write_schematic), semantic/UUID helpers, CLI
packages/verification/    RULE_PACK_V0, ERC, report/HTML, attach_evidence hook
packages/transactions/    apply_operations, semantic_diff, export_branch_diff, compile_temp_branch
packages/benchmarks/      first-pack mutation benchmark + RunManifest + CI hardware check
packages/evidence/        EvidenceService, seed catalog, store
packages/agent/           Planner (default off), DeterministicRemediationBackend, DecisionTelemetry
packages/component-library/  30 ComponentProfile entries + registry
packages/simulation/      Stub / early models
services/worker/          Redis jobs: verify_design, run_erc
infra/local-compose.yml   Postgres(pgvector), Redis, MinIO
infra/docker/kicad-cli/   KiCad 10 CLI image wrapper
tests/fixtures/golden/    10 clean IR goldens + output_conflict
tests/fixtures/kicad/     rc_divider, hierarchy/, shared_sheet/, bus/, ERC JSON fixture
tests/mutation/           single-fault IR mutators (10)
```

## What works today

### Circuit IR
Pydantic v2 models in `packages/circuit-ir`. Nets are hyperedges (multi-pin). Export schemas via `python scripts/export_schemas.py`.

### KiCad ingest
- Lossless S-expression AST parse/serialize
- Geometric connectivity → nets
- Normalize symbols/pins/labels/power into IR
- **Hierarchy / multi-sheet ingest** (root + child sheets; sheet-pin ↔ hierarchical_label merge)
- **Shared-sheet multi-instance** ingest (`fixtures/kicad/shared_sheet/`)
- **Bus members** (`fixtures/kicad/bus/` — vector labels, `bus` / `bus_entry`)
- UUID helpers: `uuid_fingerprint`, `uuid_equal`, `collect_ast_uuids`
- Semantic round-trip helpers
- Emit: `emit_schematic_ast` / `emit_schematic_text` / `write_schematic` — **connectivity-faithful** (synthetic geometry; flat single-file; not lossless multi-sheet rewrite)
- CLI: `python -m pcb_ai_kicad_adapter path.kicad_sch [--rules] [--report] [--html out.html] [-o out.json] [--emit out.kicad_sch]`
- API: `POST /v1/ingest/schematic` (multipart file)

### Deterministic rules (`RULE_PACK_V0`)
- `struct.schema_validity`
- `struct.unique_references`
- `struct.pin_existence`
- `elec.output_conflict`
- `elec.undriven_input` (digital_in, analog_in, reset, enable, boot, clock)
- `elec.power_source` (power-class nets exempt as board VIN)
- `elec.open_drain_pullup` (open_drain endpoints or protocol=i2c need passive→power pull-up)
- `elec.voltage_domain` (explicit pin/net voltage_domain strings must agree on a net)
- `elec.polarity` (opt-in `attributes.polarized` + positive/negative pins; flags +on-GND/−on-power)
- `struct.footprint_presence` (MCU/sensor/regulator/connector/… must declare `footprint_ref`; passives/OTHER exempt)

### ERC
- Parse KiCad ERC JSON + classic `.rpt` → `Finding` (`source=kicad_erc`)
- Map to component refs/UUIDs when Design available
- Runner modes: local CLI, Docker, offline `report_path` / mock (pytest uses fixtures; Docker not required)
- Worker job `type: run_erc`

### Review artifacts
- `build_review_report()` → findings, summary, net fragments (current or before/after)
- `render_html_report()` → self-contained HTML
- API: `POST /v1/reviews`, `POST /v1/reviews/html`
- Benchmark: `python -m pcb_ai_benchmarks -o reports/run-manifest.json` (**111** cases: 10 clean × 10 mutations + conflict fixture; all pass)
- CI hardware check: `python -m pcb_ai_benchmarks.ci_check` (offline ERC fixture; no Docker KiCad)

### Component profiles (30 / target 20–30)
Curated `ComponentProfile` registry in `packages/component-library` (MCU, sensors, regulators, transceivers, bridges, protection, connectors, programming, passives, switches). Lookup via `load_all` / `get_by_mpn` / `list_by_class`.

### Evidence (foundation)
- `EvidenceService` + seed catalog + JSON store
- Verification hook: `attach_evidence(findings)` enriches findings with citations
- Not yet a full datasheet ingestion / retrieval pipeline

### Agent / transactions / temp-branch
- Deterministic remediations (`pcb_ai_agent.remediation` / `DeterministicRemediationBackend`)
- `Planner(enabled=False)` by default — opt-in only
- Expanded `apply_operations` + `export_branch_diff` (semantic IR before/after; `production_mutation: false`)
- **`compile_temp_branch` / `emit_design_to_temp`** — ingest → apply ops on IR copy → `write_schematic` under `dest_dir` (never overwrites production path); emit mode `connectivity_faithful`
- API: `POST /v1/proposals` (typed ops on a Design copy; registers proposal for telemetry)
- API: `POST /v1/temp-branch` (multipart schematic + operations JSON → temp `.kicad_sch` text + branch_diff)

### Approval telemetry
- `DecisionRecord` / `DecisionTelemetry` (in-memory default; optional JSONL via `PCB_AI_DECISION_TELEMETRY_PATH`)
- API: `POST /v1/proposals/{proposal_id}/decision`, `POST /v1/decisions`, `GET /v1/decisions`

## How to run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\install_dev.ps1
pytest
```

Optional infra (Docker Desktop):

```powershell
docker compose -f infra/local-compose.yml up -d
uvicorn pcb_ai_api.main:app --reload --app-dir apps/api/src
```

Smoke review:

```powershell
python -m pcb_ai_kicad_adapter tests/fixtures/kicad/rc_divider.kicad_sch --report --html reports/rc_divider.html -o reports/rc_divider.json
python -m pcb_ai_benchmarks -o reports/run-manifest.json
python -m pcb_ai_benchmarks.ci_check -o reports/ci-hardware-check.json
```

CI hardware check (`python -m pcb_ai_benchmarks.ci_check` / `pcb-ai-ci-check`): ingest sample schematic → RULE_PACK_V0 → optional offline ERC fixture. Exit `0` if rules have no `error`/`critical` findings and ERC parse succeeds; `1` on unexpected blocking rule findings or ERC runner failure; `2` on missing inputs / ingest errors. Intentional ERC fixture findings are recorded but do not fail the job. GitHub Actions: `.github/workflows/ci.yml`.

Notes:
- Windows shell needs unrestricted permissions in Cursor if sandbox is unavailable.
- Python 3.12+ (dev machine has also run on 3.14).
- `uv` / Docker may be missing; code paths should stay offline-testable.

## Tests

Expect **231 passed** after Phase A gap reconcile (`pytest`). Key suites:
- `tests/test_golden_fixtures.py`, `test_rules.py`, `test_mutation_rules.py`
- `tests/test_parser.py`, `test_roundtrip_kicad.py`
- `tests/test_erc.py`, `test_report.py`, `test_benchmark_manifest.py`, `test_ci_hardware_check.py`, `test_api.py`
- `tests/test_agent.py`, `test_transactions.py`, `test_temp_branch.py`, `test_decision_telemetry.py`
- `tests/test_evidence.py`, `test_component_library.py`

## Remaining gaps (non-blocking for Phase B gate)

1. **Lossless multi-file emit:** emit remains a flat connectivity sketch — no child `.kicad_sch` rewrite, `(sheet …)` symbols, or hierarchical pins as a multi-file project (see `tests/roundtrip/README.md`).
2. **Emit geometry / bus fidelity:** synthetic star wires; advanced KiCad bus aliases beyond `NAME[M..N]` / `{A B}` not expanded.
3. **Evidence depth:** seed catalog only — no full datasheet ingestion / retrieval pipeline.
4. Then: **Phase B layout** (PCB IR + DRC + placement/routing), then Phase C prompt-to-CAD.

## Explicitly not built yet

- React review UI / real KiCad plugin
- LLM planner enabled in production (seam exists; default **off**; deterministic backend only)
- Lossless layout-preserving / multi-file KiCad hierarchy rewrite on emit
- Deep datasheet evidence pipeline
- ngspice simulation jobs
- Altium support
- **Phase B:** AI placement/routing / board redraw
- **Phase C:** prompt-to-CAD
- Live ERC in CI (image exists; unit tests are fixture-based)
- Full §7 rule pack beyond the current 10 high-precision checks

## Recommended next work

Prioritize in order:
1. **Phase B:** PCB IR + DRC foundations and layout/redraw agent seams.
2. Optionally harden normalize/emit fidelity if layout workflows need multi-file hierarchy round-trip.
3. Grow evidence beyond seed catalog when remediation quality needs datasheet citations.
4. Bounded prompt-to-CAD (Phase C) only after Phase B gates in the plan.

## Guardrails for the next agent

- Prefer small, test-backed diffs over broad refactors.
- Do not enable LLM CAD mutation of production files; branch-only + human approval.
- Phase A gates are largely met — start Phase B layout work per the plan; do not reopen broad Phase A scope for residual emit limits unless blocked.
- Keep ERC/DRC/SPICE success from being treated as product-level correctness.
- Commit only when the user asks; never force-push `main`.
- Read `pcb_ai_implementation_plan_v0.md` (v0.2) before changing product direction.

## Key entry files

| Concern | Start here |
|---------|------------|
| IR models | `packages/circuit-ir/src/pcb_ai_circuit_ir/models.py` |
| Rules | `packages/verification/src/pcb_ai_verification/rules.py` |
| Review report | `packages/verification/src/pcb_ai_verification/report.py` |
| HTML report | `packages/verification/src/pcb_ai_verification/html_report.py` |
| Evidence hook | `packages/verification/src/pcb_ai_verification/evidence.py` |
| Evidence service | `packages/evidence/src/pcb_ai_evidence/service.py` |
| Component profiles | `packages/component-library/src/pcb_ai_component_library/registry.py` |
| KiCad normalize / hierarchy | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/normalize.py`, `hierarchy.py` |
| Emit / write_schematic | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/emit.py` |
| UUID / semantic helpers | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/semantic.py` |
| ERC | `packages/verification/src/pcb_ai_verification/erc_*.py` |
| Mutations | `tests/mutation/ir_mutators.py` |
| Benchmark manifest | `packages/benchmarks/src/pcb_ai_benchmarks/manifest.py` |
| CI hardware check | `packages/benchmarks/src/pcb_ai_benchmarks/ci_check.py` |
| Agent / remediations / telemetry | `packages/agent/src/pcb_ai_agent/` |
| Transactions / temp-branch | `packages/transactions/src/pcb_ai_transactions/` |
| Proposals + decisions API | `apps/api/src/pcb_ai_api/routes/proposals.py` |
| Temp-branch API | `apps/api/src/pcb_ai_api/routes/temp_branch.py` |
| API | `apps/api/src/pcb_ai_api/` |
