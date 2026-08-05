# Architecture notes

See `pcb_ai_implementation_plan_v0.md` at the repository root for the product decision,
Phase A MVP architecture, Circuit IR, rule pack, and foundations → layout → prompt-to-CAD timeline.

## Source of truth

1. Circuit IR for AI reasoning
2. Deterministic tools for syntax, graph integrity, and rule compliance (later: DRC/constraints for layout)
3. Human approval for electrical and layout changes that affect production CAD
4. Branch-only reversible patches — never direct production CAD mutation by the LLM
5. North star: coding-agent loop for hardware; Phase B layout then Phase C prompt-to-CAD after Phase A gates

## Native verification (KiCad ERC)

- Image: `infra/docker/kicad-cli/` (wraps official `kicad/kicad`)
- Parser / mapper: `pcb_ai_verification.erc_parse` / `erc_map` → `Finding` with `source="kicad_erc"`
- Runner: `pcb_ai_verification.erc_runner.run_schematic_erc` (local CLI, Docker, or fixture/mock)
- Worker job: `type: "run_erc"` in `pcb_ai_worker`
