# ADR 0001: Verification-first KiCad MVP

## Status

Accepted

## Context

Autonomous layout and prompt-to-native-CAD generation are high-risk for electrical correctness
and CAD round-trip integrity.

## Decision

Build a verification-first KiCad copilot: ingest → typed Circuit IR → deterministic checks →
evidence → reversible typed operations → temporary branch → ERC/regression → human approval.

## Consequences

- PostgreSQL (+ pgvector later) instead of a graph DB for MVP
- Curated 20–30 component profiles before broad datasheet ingestion
- LLM planner disabled until deterministic path meets precision gates
- Altium and routing deferred
