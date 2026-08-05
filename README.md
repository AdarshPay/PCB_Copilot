# PCB Copilot

Verification-first KiCad copilot for schematic review and bounded schematic generation.

The circuit IR is the source of truth. Deterministic tools own syntax, graph integrity, and rule compliance. The LLM may propose typed operations but never mutates production CAD files directly. Human approval is required for electrical changes.

## Current milestone (Sprint day 10+)

- Machine-readable `ReviewReport` with findings, net fragments, and summary
- HTML semantic review report (`POST /v1/reviews/html`, CLI `--html`)
- Reproducible first-pack benchmark run manifest (`python -m pcb_ai_benchmarks`)
- Offline CI hardware check (`python -m pcb_ai_benchmarks.ci_check`) + GitHub Actions
- Prior: KiCad ingest/round-trip, ERC normalization, first-pack deterministic rules + mutations

Sprint exit criterion: ingest, normalize, check, round-trip, and report one real KiCad schematic **without** an LLM.

## Repository layout

```text
apps/
  api/              FastAPI review service
  web/              React/TypeScript review workspace (stub)
  kicad-plugin/     Thin KiCad integration (stub)
packages/
  circuit-ir/       Typed canonical representation
  kicad-adapter/    Parse / compile / version compatibility
  verification/     Deterministic rule engine
  evidence/         Documents, facts, citations
  transactions/     Edit operations, diff, rollback
  agent/            Prompts, tools, structured planning
  simulation/       ngspice jobs and assertions
  benchmarks/       Datasets, mutation engine, scoring
  component-library/ Curated component profiles
services/
  worker/           Async jobs (ERC, parsing, retrieval, simulation)
schemas/            JSON Schema exports
tests/              Fixtures, golden, roundtrip, mutation
infra/              Docker Compose, migrations
docs/               Architecture and decisions
```

## Prerequisites

- Python 3.12+
- Docker Desktop (for Postgres, Redis, MinIO)

## Quick start

```powershell
# Create a virtualenv and install packages in editable mode
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\install_dev.ps1

# Start infrastructure (requires Docker Desktop)
docker compose -f infra/local-compose.yml up -d

# Run API
uvicorn pcb_ai_api.main:app --reload --app-dir apps/api/src

# Run tests
pytest

# Export JSON Schema documents
python scripts/export_schemas.py

# HTML + JSON review from a schematic
python -m pcb_ai_kicad_adapter tests/fixtures/kicad/rc_divider.kicad_sch --report --html reports/rc_divider.html -o reports/rc_divider.json

# First-pack mutation benchmark manifest
python -m pcb_ai_benchmarks -o reports/run-manifest.json

# CI hardware check (ingest + RULE_PACK_V0 + offline ERC fixture; no Docker KiCad)
python -m pcb_ai_benchmarks.ci_check -o reports/ci-hardware-check.json
```

### Native ERC (optional Docker)

Pytest uses `tests/fixtures/kicad/rc_divider_erc.json` and does not require KiCad. To run live ERC when Docker is available:

```powershell
docker build -t pcb-ai-kicad-cli:local -f infra/docker/kicad-cli/Dockerfile infra/docker/kicad-cli
docker run --rm -v ${PWD}/tests/fixtures/kicad:/work -w /work pcb-ai-kicad-cli:local `
  sch erc --format json --severity-all --output rc_divider_erc_live.json rc_divider.kicad_sch
```

See `infra/docker/kicad-cli/README.md` for worker payload examples (`type: run_erc`).

## Design constraints

- Target KiCad 10 first; use documented S-expression parsing + `kicad-cli`, not deprecated SWIG bindings
- PostgreSQL (+ pgvector later for evidence); no separate vector DB in MVP
- Patches are reversible and branch-only
- No routing / autonomous layout in MVP
