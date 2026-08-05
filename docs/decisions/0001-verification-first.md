# ADR 0001: Verification-first foundation, then layout, then prompt-to-CAD

## Status

Accepted (updated 2026-08-04)

## Context

The long-term product goal is an agentic hardware workflow analogous to coding agents in
software engineering: intent → tool-backed edits → deterministic checks → human-approvable
CAD diffs.

Autonomous layout and prompt-to-native-CAD generation are high-risk for electrical correctness
and CAD round-trip integrity if attempted before ingest, IR, verification, and reversible
transactions work.

## Decision

1. **Phase A (MVP):** Build a verification-first KiCad copilot: ingest → typed Circuit IR →
   deterministic checks → evidence → reversible typed operations → temporary branch →
   ERC/regression → human approval.
2. **Phase B:** After Phase A gates, add AI layout / redraw (placement + routing) using the
   same propose/verify/repair/approve loop and DRC as a gate.
3. **Phase C:** After a working layout loop, add bounded prompt-to-CAD generation on top of
   the same stack.

Do not skip ahead to B or C before A precision and transaction gates are met.

## Consequences

- PostgreSQL (+ pgvector later) instead of a graph DB for MVP
- Curated 20–30 component profiles before broad datasheet ingestion
- LLM planner disabled until deterministic path meets precision gates
- Altium deferred as a later CAD target
- Routing/layout deferred to Phase B (not abandoned)
- Prompt-to-CAD deferred to Phase C
- Success metric for later phases is approvable, check-gated CAD diffs — not one-shot pretty boards
