# Architecture notes

See `pcb_ai_implementation_plan_v0.md` at the repository root for the product decision,
MVP architecture, Circuit IR, rule pack, and 30/60/90 plan.

## Source of truth

1. Circuit IR for AI reasoning
2. Deterministic tools for syntax, graph integrity, and rule compliance
3. Human approval for electrical changes
4. Branch-only reversible patches — never direct production CAD mutation by the LLM
