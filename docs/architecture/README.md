# Architecture notes

See `pcb_ai_implementation_plan_v0.md` at the repository root for the product decision,
MVP architecture, Circuit IR, rule pack, and 30/60/90 plan.

## Source of truth

1. Circuit IR for AI reasoning
2. Deterministic tools for syntax, graph integrity, and rule compliance
3. Human approval for electrical changes
4. Branch-only reversible patches — never direct production CAD mutation by the LLM

## Native verification (KiCad ERC)

- Image: `infra/docker/kicad-cli/` (wraps official `kicad/kicad`)
- Parser / mapper: `pcb_ai_verification.erc_parse` / `erc_map` → `Finding` with `source="kicad_erc"`
- Runner: `pcb_ai_verification.erc_runner.run_schematic_erc` (local CLI, Docker, or fixture/mock)
- Worker job: `type: "run_erc"` in `pcb_ai_worker`
