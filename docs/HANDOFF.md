# Agent handoff — PCB Copilot

Date: 2026-08-04  
Repo: https://github.com/AdarshPay/PCB_Copilot  
Branch: `main`  
Plan of record: `pcb_ai_implementation_plan_v0.md` (v0.2)

## Product in one sentence

**North star:** coding-agent workflow for hardware (intent → tools → checks → approvable CAD diff).  
**Current MVP (Phase A):** verification-first KiCad schematic copilot — ingest → typed Circuit IR → deterministic checks (+ optional KiCad ERC) → review report. The LLM must **not** mutate production CAD; patches are typed, reversible, and human-approved.  
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

**Sprint exit criterion (met):** one schematic can be ingested, normalized, checked, round-tripped, and reported **without an LLM**.

**Next horizon:** Finish remaining Day 30 scale (more clean projects / mutations toward 10/100), then Day 60 Phase A complete (profiles → evidence → typed LLM remediations → transactions). **Gate to Phase B** AI layout/redraw, then Phase C prompt-to-CAD. Do **not** start layout or prompt-to-CAD until Phase A gates in the plan are met.

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
packages/benchmarks/      first-pack mutation benchmark + RunManifest + CI hardware check
packages/evidence|agent|simulation|component-library/  stubs / early models
services/worker/          Redis jobs: verify_design, run_erc
infra/local-compose.yml   Postgres(pgvector), Redis, MinIO
infra/docker/kicad-cli/   KiCad 10 CLI image wrapper
tests/fixtures/golden/    IR JSON fixtures (rc_divider, i2c_sensor, ldo_rail, uart_bridge, output_conflict)
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
- `elec.open_drain_pullup` (open_drain endpoints or protocol=i2c need passive→power pull-up)
- `elec.voltage_domain` (explicit pin/net voltage_domain strings must agree on a net)
- `elec.polarity` (opt-in `attributes.polarized` + positive/negative pins; flags +on-GND/−on-power)
- `struct.footprint_presence` (MCU/sensor/regulator/connector/… must declare `footprint_ref`; passives/OTHER exempt)

### ERC
- Parse KiCad ERC JSON + classic `.rpt` → `Finding` (`source=kicad_erc`)
- Map to component refs/UUIDs when Design available
- Runner modes: local CLI, Docker, offline `report_path` / mock (pytest uses fixtures; Docker not required)
- Worker job `type: run_erc`

### Review artifacts (Day 10)
- `build_review_report()` → findings, summary, net fragments (current or before/after)
- `render_html_report()` → self-contained HTML
- API: `POST /v1/reviews`, `POST /v1/reviews/html`
- Benchmark: `python -m pcb_ai_benchmarks -o reports/run-manifest.json` (41 cases: 4 clean × 9 mutations + conflict fixture)
- CI hardware check: `python -m pcb_ai_benchmarks.ci_check` (offline ERC fixture; no Docker KiCad)

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

Expect **94 passed** after Day 30 completion (`pytest`). Key suites:
- `tests/test_golden_fixtures.py`, `test_rules.py`, `test_mutation_rules.py`
- `tests/test_parser.py`, `test_roundtrip_kicad.py`
- `tests/test_erc.py`, `test_report.py`, `test_benchmark_manifest.py`, `test_ci_hardware_check.py`, `test_api.py`

## Explicitly not built yet

- React review UI / real KiCad plugin
- LLM planner (disabled by design until precision gates)
- Full transaction compiler → temporary KiCad branch workflow
- Curated 20–30 component profiles + datasheet evidence service
- ngspice simulation jobs
- Altium support
- **Phase B:** AI placement/routing / board redraw
- **Phase C:** prompt-to-CAD
- Live ERC in CI (image exists; unit tests are fixture-based)
- Full §7 rule pack beyond the current 10 high-precision checks
- Day 30 scale target of 10 clean projects / 100 mutations (currently 4 clean goldens + 1 conflict fixture)

## Recommended next work (toward Day 60 → Phase B layout)

Prioritize in order:
1. **More clean KiCad projects + mutations** toward 10 clean / 100 mutations; keep project-family splits in mind.
2. Harden KiCad normalize for hierarchy / multi-sheet / real libraries (round-trip UUID/hierarchy research item).
3. **Day 60 / Phase A complete:** curated component profiles → datasheet evidence → typed LLM remediations → transaction compiler (temp KiCad branch + human approve). This is the **gate to Phase B**.
4. Only after Phase A gates: PCB IR + DRC + layout agent (Phase B), then bounded prompt-to-CAD (Phase C).

(Day 30 rule count and CI hardware-check are done — 10 checks in `RULE_PACK_V0`; see `ci_check` + `.github/workflows/ci.yml`.)

## Guardrails for the next agent

- Prefer small, test-backed diffs over broad refactors.
- Do not enable LLM CAD mutation of production files; branch-only + human approval.
- Do not start routing / autonomous layout or prompt-to-CAD until Phase A gates in the plan are met.
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
| KiCad normalize | `packages/kicad-adapter/src/pcb_ai_kicad_adapter/normalize.py` |
| ERC | `packages/verification/src/pcb_ai_verification/erc_*.py` |
| Mutations | `tests/mutation/ir_mutators.py` |
| Benchmark manifest | `packages/benchmarks/src/pcb_ai_benchmarks/manifest.py` |
| CI hardware check | `packages/benchmarks/src/pcb_ai_benchmarks/ci_check.py` |
| API | `apps/api/src/pcb_ai_api/` |
