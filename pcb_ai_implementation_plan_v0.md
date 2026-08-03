# PCB AI Implementation Plan v0.1

Date: 2026-07-31

## 1. Product decision

Build a verification-first KiCad copilot for schematic review and bounded schematic generation. Do not begin with autonomous layout or prompt-to-native-CAD generation.

Initial supported domain:
- Low-voltage embedded boards
- Microcontrollers and common sensors
- LDO and simple buck power stages
- I2C, SPI, UART, CAN, and RS-485 interfaces
- Connectors, protection, programming, and test circuitry

Initial user actions:
1. Import a KiCad project.
2. Normalize it into a typed circuit IR.
3. Run deterministic structural and electrical checks.
4. Retrieve evidence for findings.
5. Propose a reversible set of edits.
6. Compile edits into a branch copy of the KiCad project.
7. Run KiCad ERC and semantic-regression checks.
8. Present a diff for engineer approval.

## 2. Architectural principles

1. The circuit IR is the source of truth for AI reasoning.
2. The LLM may propose typed operations but may not directly mutate production CAD files.
3. Every operation has preconditions, postconditions, evidence, confidence, and rollback data.
4. Deterministic tools decide syntax, graph integrity, and rule compliance.
5. Simulation can add evidence but cannot prove package-level correctness.
6. Human approval is required for electrical changes.
7. All data and model versions are recorded for replay.

## 3. MVP system architecture

```text
KiCad project
    |
    v
KiCad adapter ----> lossless S-expression AST
    |                         |
    v                         v
Typed circuit IR <---- semantic normalization
    |
    +----> deterministic verifier
    +----> evidence retrieval
    +----> LLM planner -> typed edit operations
    +----> semantic diff
    |
    v
transaction compiler -> temporary KiCad branch
    |
    +----> kicad-cli ERC
    +----> graph-equivalence checks
    +----> optional ngspice simulation
    |
    v
review report -> human approval -> export
```

## 4. Recommended technology stack

### Core
- Python 3.12
- Pydantic v2 for typed schemas
- FastAPI for the API
- PostgreSQL for projects, revisions, rules, findings, and provenance
- pgvector only for evidence retrieval; do not add a separate vector database initially
- NetworkX for early graph algorithms; replace hot paths later if needed
- S3-compatible object storage for source projects, generated branches, reports, and datasheets
- Redis plus a lightweight worker queue for prototype jobs

### Frontend
- React/TypeScript web review workspace
- A thin KiCad add-on that opens the current project in the review service and applies approved patches
- Semantic diff views organized by components, pins, nets, requirements, and evidence

### CAD and simulation
- KiCad 10 as the primary compatibility target
- Direct parsing and writing of documented KiCad S-expression files behind an adapter
- Official KiCad IPC API for supported live-editor interactions
- `kicad-cli sch erc` and `kicad-cli pcb drc` for native checks
- ngspice in batch mode for the first simulation jobs

### AI
- Existing hosted or open-weight language model with structured JSON outputs
- No foundation-model training during MVP
- Curated component facts plus retrieval from datasheets and application notes
- Maximum three-step propose/verify/repair loop

## 5. Monorepo layout

```text
pcb-ai/
  apps/
    api/                  # FastAPI service
    web/                  # review UI
    kicad-plugin/         # thin KiCad integration
  packages/
    circuit-ir/           # typed canonical representation
    kicad-adapter/        # parse, compile, version compatibility
    verification/         # deterministic rule engine
    evidence/             # documents, facts, citations
    agent/                # prompts, tools, structured planning
    transactions/         # edit operations, diff, rollback
    simulation/           # ngspice jobs and assertions
    benchmarks/           # datasets, mutation engine, scoring
    component-library/    # curated component profiles
  services/
    worker/               # ERC, parsing, retrieval, simulation jobs
  schemas/
    circuit-ir.schema.json
    transaction.schema.json
    finding.schema.json
  tests/
    fixtures/
    golden/
    roundtrip/
    mutation/
  infra/
    docker/
    migrations/
    local-compose.yml
  docs/
    architecture/
    rules/
    benchmark/
    decisions/
```

## 6. Circuit IR v0

```text
Design
- id, source_tool, source_version, revision
- requirements[]
- blocks[]
- components[]
- nets[]
- assertions[]
- evidence_refs[]

Component
- reference
- manufacturer_part_number
- value
- functional_class
- symbol_ref
- footprint_ref
- pins[]
- attributes
- source_location

Pin
- number
- name
- electrical_role
- interface_role
- voltage_domain
- constraints[]

Net
- name
- endpoints[]
- class
- voltage_domain
- protocol
- constraints[]

Operation
- type
- target
- preconditions[]
- payload
- evidence_refs[]
- expected_checks[]
- risk_tier

Finding
- rule_id
- severity
- objects[]
- explanation
- evidence_refs[]
- confidence
- remediation_operations[]
```

Treat nets as hyperedges connecting multiple component pins. Store the relational representation in PostgreSQL first; expose graph projections for algorithms rather than introducing Neo4j during the prototype.

## 7. First deterministic rule pack

### Structural
1. Parse and schema validity
2. Unique references and UUIDs
3. Symbol existence
4. Footprint existence
5. Referenced pin existence
6. Symbol-to-footprint pin-count and pin-map consistency
7. No-connect marker consistency
8. Dangling wire and label checks
9. Duplicate or conflicting net labels
10. Schematic/PCB parity when a board exists

### Electrical semantics
11. Output-to-output conflicts
12. Undriven required inputs
13. Power-input nets without a valid source
14. Voltage-domain incompatibility
15. Polarity-sensitive device orientation
16. Open-drain bus without required pull-up
17. Reset or enable pin missing a defined state
18. Required boot/configuration strap missing
19. Regulator input/output voltage and current constraint violations
20. Missing required local support component from a curated component profile

Do not launch with broad AI-generated findings. Start with high-precision rules whose assumptions are explicit.

## 8. Component knowledge strategy

Begin with a curated library of 20-30 components, not arbitrary web-scale part ingestion.

Each component profile should contain:
- Manufacturer and exact orderable package
- Verified symbol and footprint mapping
- Pin-role ontology
- Absolute maximum and recommended operating ranges
- Supply domains
- Required and recommended support components
- Boot/reset/configuration requirements
- Interface electrical characteristics
- Approved reference circuits
- Simulation model references when available
- Datasheet edition, page, table, and figure provenance

Suggested first families:
- One STM32 or RP2040-class MCU family
- Common I2C temperature, IMU, and environmental sensors
- One CAN transceiver
- One RS-485 transceiver
- Common LDOs
- One simple buck regulator family
- USB-to-UART bridge
- ESD and reverse-polarity protection parts

## 9. Benchmark v0

### Dataset
- 20 clean, licensed KiCad projects
- 5 circuit families
- 10 mutation categories
- At least 200 total mutated cases
- Project-family split between development and held-out evaluation

### Mutations
- Swapped power and ground pin
- Wrong package pin mapping
- Missing decoupling capacitor
- Missing I2C pull-ups
- Invalid pull-up voltage
- Floating reset or enable pin
- Output-to-output connection
- Regulator voltage-range violation
- Reversed polarized component
- Incorrect connector or programming-header mapping

### Metrics
- Native parse success
- Lossless round-trip success
- Precision and recall by fault class
- Severity-weighted false-negative rate
- Evidence correctness
- Patch compilation rate
- ERC regression count
- Engineer acceptance and edit rate
- Review time reduction

## 10. First two-week engineering sprint

### Days 1-2: foundations
- Create monorepo and local Docker environment
- Define Circuit IR, Finding, Evidence, and Operation schemas
- Add golden JSON fixtures for three tiny circuits

### Days 3-5: KiCad ingestion
- Parse `.kicad_sch` into a lossless AST
- Normalize components, pins, labels, and nets into Circuit IR
- Add round-trip tests that produce no semantic changes

### Days 6-7: native verification
- Containerize KiCad CLI
- Run ERC and parse reports into normalized findings
- Add source-object mapping from findings back to schematic UUIDs

### Days 8-9: first rules
- Implement unique reference, pin existence, output conflict, undriven input, and power-source checks
- Create mutation tests for each rule

### Day 10: review artifact
- Generate a machine-readable and HTML semantic review report
- Show before/after net fragments and rule evidence
- Record benchmark results in a reproducible run manifest

Sprint exit criterion: one real KiCad schematic can be ingested, normalized, checked, round-tripped, and reported without an LLM.

## 11. 30/60/90-day plan

### Day 30
- 10 deterministic checks
- 10 clean projects and 100 mutations
- Lossless or semantically equivalent KiCad round trips
- HTML review report
- CI command for repository-based hardware checks

### Day 60
- 20-30 curated component profiles
- Datasheet evidence service
- First LLM-generated typed remediation suggestions
- Transaction compiler and temporary branch workflow
- Engineer approval/rejection telemetry

### Day 90
- KiCad add-on prototype
- 20 clean projects and 200+ mutations
- One bounded generation flow, such as MCU + I2C sensor + power + programming header
- ERC and semantic repair loop
- Small external design-partner pilot

## 12. Research workstreams

1. Compare the IRs and generation APIs used by pcbGPT, SchGen, PCBSchemaGen, circuit-synth, SKiDL, and atopile.
2. Reproduce at least one public schematic-generation benchmark before designing a new model.
3. Test whether KiCad 10 schematic files can be round-tripped with exact UUID and hierarchy preservation.
4. Define a pin-role ontology that can express power, analog, digital, open-drain, clock, reset, boot, and package-specific functions.
5. Evaluate datasheet extraction accuracy separately for prose, pin tables, electrical tables, equations, and reference schematics.
6. Determine which component facts must be human-curated versus machine-extracted.
7. Build a fault taxonomy from real schematic review comments and public design mistakes.
8. Measure whether LLM repair adds value after deterministic checks, rather than measuring attractive schematic appearance.
9. Study licensing of KiCad libraries, open-hardware projects, manufacturer documents, and research datasets before ingestion.
10. Defer placement/routing work until the schematic-review metrics meet launch gates; use PCBWorld as the later routing baseline.

## 13. Immediate decisions

- Target KiCad 10 first.
- Use documented file parsing plus KiCad CLI; do not build on deprecated SWIG bindings.
- Use PostgreSQL rather than a graph database initially.
- Build a component ontology and rule engine before any fine-tuning.
- Curate a small component set and benchmark before broad datasheet ingestion.
- Make patches reversible and branch-only.
- Keep Altium as phase two; begin API/SDK access work in parallel only after the KiCad core is stable.
- Do not implement routing in the MVP.

## 14. Main technical risks

1. KiCad round-trip corruption or version fragility
2. Incorrect symbol-footprint-pin mappings
3. Datasheet evidence extracted from the wrong package or revision
4. Low-precision findings that cause alert fatigue
5. Lack of legally usable defective schematics
6. Over-scoping the component universe
7. Treating ERC or SPICE success as product-level correctness
8. Agent edits that are syntactically valid but semantically destructive

## 15. First implementation milestone

The first meaningful milestone is not “generate a PCB.” It is:

> Given a KiCad schematic, produce a deterministic semantic graph, identify five injected electrical faults with high precision, cite the rule or component evidence, generate reversible candidate repairs, and prove that the approved repair compiles and does not introduce new ERC violations.

