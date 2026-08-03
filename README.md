# PCB Copilot

Verification-first KiCad copilot for schematic review and bounded schematic generation.

The circuit IR is the source of truth. Deterministic tools own syntax, graph integrity, and rule compliance. The LLM may propose typed operations but never mutates production CAD files directly. Human approval is required for electrical changes.

## Current milestone (Sprint days 1–2)

- Monorepo and local Docker environment
- Circuit IR, Finding, Evidence, and Operation schemas
- Golden JSON fixtures for three tiny circuits

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
```

## Design constraints

- Target KiCad 10 first; use documented S-expression parsing + `kicad-cli`, not deprecated SWIG bindings
- PostgreSQL (+ pgvector later for evidence); no separate vector DB in MVP
- Patches are reversible and branch-only
- No routing / autonomous layout in MVP
