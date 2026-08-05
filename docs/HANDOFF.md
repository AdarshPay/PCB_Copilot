# Agent handoff — PCB Copilot

Date: 2026-08-04  
Repo: https://github.com/AdarshPay/PCB_Copilot  
Branch: `main`  
Plan of record: `pcb_ai_implementation_plan_v0.md`

## Product in one sentence

Verification-first KiCad schematic copilot: ingest a schematic → typed Circuit IR → deterministic checks (+ optional KiCad ERC) → review report. The LLM must **not** mutate production CAD; patches are typed, reversible, and human-approved later.

## Sprint status

| Sprint days | Status | Notes |
|-------------|--------|-------|
| 1–2 Foundations | Done | Monorepo, schemas, Docker compose, golden IR fixtures |
| 3–5 KiCad ingest | Done | Parse/normalize/round-trip `.kicad_sch` |
| 6–7 Native ERC | Done | ERC→Finding, Docker image, offline tests |
| 8–9 First rules + mutations | Done | Five first-pack rules + single-fault mutations |
| 10 Review artifact | Done (local; push with this handoff) | JSON + HTML report, run manifest |

**Sprint exit criterion (met):** one schematic can be ingested, normalized, checked, round-tripped, and reported **without an LLM**.

**Next horizon:** Day 30 goals in the plan (10 checks, more fixtures/mutations, CI hardware-check command). Do **not** jump to layout/routing or broad LLM generation.

## Architecture (source of truth)

```text
.kicad_sch → kicad-adapter (AST) → Circuit IR
                ↓
     verification rules + optional ERC
                ↓
     ReviewReport (JSON) + HTML report
                ↓
     (later) typed Operations → temp KiCad branch → human approve
```

Non-negotiables from the plan:
1. Circuit IR is the reasoning source of truth.
2. Deterministic tools own syntax / graph / rules.
3. Human approval required for electrical changes.
4. PostgreSQL (+ pgvector later); no Neo4j in MVP.
5. Target KiCad 10; use file parse + `kicad-cli`, not deprecated SWIG bindings.

## Repo map

```text
apps/api/                 FastAPI: /health, /v1/reviews, /v1/reviews/html, /v1/ingest/schematic
apps/web/                 Stub only
apps/kicad-plugin/        Stub only
packages/circuit-ir/      Design, Component, Pin, Net, Finding, Operation, ReviewReport, NetFragment
packages/kicad-adapter/   parser, connectivity, normalize, emit, semantic, CLI (__main__)
packages/verification/    RULE_PACK_V0, ERC parse/runner, build_review_report, HTML renderer
packages/transactions/    apply_operations, semantic_diff (prototype)
packages/benchmarks/      first-pack mutation benchmark + RunManifest
packages/evidence|agent|simulation|component-library/  stubs / early models
services/worker/          Redis jobs: verify_design, run_erc
infra/local-compose.yml   Postgres(pgvector), Redis, MinIO
infra/docker/kicad-cli/   KiCad 10 CLI image wrapper
tests/fixtures/golden/    IR JSON fixtures
tests/fixtures/kicad/     rc_divider.kicad_sch + ERC JSON fixture
tests/mutation/           single-fault IR mutators
```

## What works today

### Circuit IR
Pydantic v2 models in `packages/circuit-ir`. Nets are hyperedges (multi-pin). Export schemas via `python scripts/export_schemas.py`.

### KiCad ingest
- Lossless S-expression AST parse/serialize
- Geometric connectivity → nets
- Normalize symbols/pins/labels/power into IR
- Semantic round-trip helpers
- CLI: `python -m pcb_ai_kicad_adapter path.kicad_sch [--rules] [--report] [--html out.html] [-o out.json] [--emit out.kicad_sch]`
- API: `POST /v1/ingest/schematic` (multipart file)

### Deterministic rules (`RULE_PACK_V0`)
- `struct.schema_validity`
- `struct.unique_references`
- `struct.pin_existence`
- `elec.output_conflict`
- `elec.undriven_input` (digital_in, analog_in, reset, enable, boot, clock)
- `elec.power_source` (power-class nets exempt as board VIN)

### ERC
- Parse KiCad ERC JSON + classic `.rpt` → `Finding` (`source=kicad_erc`)
- Map to component refs/UUIDs when Design available
- Runner modes: local CLI, Docker, offline `report_path` / mock (pytest uses fixtures; Docker not required)
- Worker job `type: run_erc`

### Review artifacts (Day 10)
- `build_review_report()` → findings, summary, net fragments (current or before/after)
- `render_html_report()` → self-contained HTML
- API: `POST /v1/reviews`, `POST /v1/reviews/html`
- Benchmark: `python -m pcb_ai_benchmarks -o reports/run-manifest.json` (13/13 first-pack cases)

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
```

Notes:
- Windows shell needs unrestricted permissions in Cursor if sandbox is unavailable.
- Python 3.12+ (dev machine has also run on 3.14).
- `uv` / Docker may be missing; code paths should stay offline-testable.

## Tests

Expect **53 passed** after Day 10 (`pytest`). Key suites:
- `tests/test_golden_fixtures.py`, `test_rules.py`, `test_mutation_rules.py`
- `tests/test_parser.py`, `test_roundtrip_kicad.py`
- `tests/test_erc.py`, `test_report.py`, `test_benchmark_manifest.py`, `test_api.py`

## Explicitly not built yet

- React review UI / real KiCad plugin
- LLM planner (disabled by design until precision gates)
- Full transaction compiler → temporary KiCad branch workflow
- Curated 20–30 component profiles + datasheet evidence service
- ngspice simulation jobs
- Altium support, placement/routing
- Live ERC in CI (image exists; unit tests are fixture-based)
- Expanding beyond ~5–6 high-precision rules to the full §7 pack

## Recommended next work (Day 30 track)

Prioritize in order:
1. **More deterministic rules** from plan §7 (pull-ups, polarity, regulator constraints, etc.) with one mutation test each — keep high precision; avoid noisy AI findings.
2. **More clean KiCad projects + mutations** toward 10 clean / 100 mutations; keep project-family splits in mind.
3. **CI command** that runs ingest + rules (+ offline ERC fixture path) on a sample project.
4. Harden KiCad normalize for hierarchy / multi-sheet / real libraries (round-trip UUID/hierarchy research item).
5. Only after precision is solid: component profiles, then evidence retrieval, then typed LLM remediations (Day 60).

## Guardrails for the next agent

- Prefer small, test-backed diffs over broad refactors.
- Do not enable LLM CAD mutation.
- Do not start routing / autonomous layout.
- Keep ERC/SPICE success from being treated as product-level correctness.
- Commit only when the user asks; never force-push `main`.
- Read `pcb_ai_implementation_plan_v0.md` before changing product direction.

## Key entry files

| Concern | Start here |
|---------|------------|
| IR models | `packages/circuit-ir/src/pcb_ai_circuit_ir/models.py` |
| Rules | `packages/verification/src/pcb_ai_verification/rules.py` |
| Review report | `packages/verification/src/pcb_ai_verification/report.py` |
| HTML report | `packages/verification/src/pcb_ai_verification/html_report.py` |
| KiCad normalize | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/normalize.py` |
| ERC | `packages/verification/src/pcb_ai_verification/erc_*.py` |
| Mutations | `tests/mutation/ir_mutators.py` |
| Benchmark manifest | `packages/benchmarks/src/pcb_ai_benchmarks/manifest.py` |
| API | `apps/api/src/pcb_ai_api/` |
