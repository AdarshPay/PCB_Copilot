# KiCad CLI image (Days 6–7)

Thin wrapper around the official [`kicad/kicad`](https://hub.docker.com/r/kicad/kicad) image for native schematic ERC / PCB DRC via `kicad-cli`. No deprecated SWIG bindings.

## Build

```powershell
docker build -t pcb-ai-kicad-cli:local -f infra/docker/kicad-cli/Dockerfile infra/docker/kicad-cli
```

Override the base tag if needed:

```powershell
docker build --build-arg KICAD_TAG=10.0 -t pcb-ai-kicad-cli:local -f infra/docker/kicad-cli/Dockerfile infra/docker/kicad-cli
```

If `kicad/kicad:10.0` is unavailable on your registry mirror, pull a nearby release tag (for example `9.0`) and set `KICAD_TAG` accordingly. The Python parser targets the KiCad 9+/10 ERC JSON schema (`sheets[].violations`).

## Run schematic ERC

```powershell
# Mount the directory that contains the .kicad_sch
docker run --rm `
  -v ${PWD}/tests/fixtures/kicad:/work `
  -w /work `
  pcb-ai-kicad-cli:local `
  sch erc --format json --severity-all --output rc_divider_erc_live.json rc_divider.kicad_sch
```

Or use the official image directly without building the wrapper:

```powershell
docker run --rm `
  -v ${PWD}/tests/fixtures/kicad:/work `
  -w /work `
  kicad/kicad:10.0 `
  sch erc --format json --severity-all --output rc_divider_erc_live.json rc_divider.kicad_sch
```

## Offline / pytest path

Unit tests parse `tests/fixtures/kicad/rc_divider_erc.json` and do **not** require Docker or `kicad-cli`.

```powershell
$env:PCB_AI_ERC_MODE = "mock"
$env:PCB_AI_ERC_MOCK_REPORT = "tests/fixtures/kicad/rc_divider_erc.json"
pytest tests/test_erc.py -q
```

## Worker job

Enqueue a Redis job with `"type": "run_erc"` and either:

- `"report_path"`: path to an existing ERC JSON (offline), or
- `"schematic_path"`: path to a `.kicad_sch` (requires local/Docker KiCad), or
- `"erc_report"`: inline ERC JSON object
