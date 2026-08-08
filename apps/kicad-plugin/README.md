# KiCad Action Plugin — PCB Copilot AI Layout (Phase B5)

Thin **KiCad 10** Action Plugin (PCB editor) that:

1. Resolves the open board / project path via `pcbnew`
2. Finds the associated `.kicad_sch`
3. `POST`s the schematic to the local API `http://127.0.0.1:8000/v1/layout`
4. Shows a summary (unrouted nets, finding counts, `proposal_id`)
5. On **Approve**: writes a sidecar `*-copilot.kicad_pcb` (never overwrites production) and records `POST /v1/proposals/{id}/decision`
6. On **Reject**: discards; optionally records a reject decision

Dependencies inside the plugin: **Python stdlib + pcbnew + wx** only.

## 5-minute demo (Windows)

### 1. Start the local API

From the repo root (venv activated, packages installed via `.\scripts\install_dev.ps1`):

```powershell
cd C:\Users\adars\Documents\PCB_Copilot
.\.venv\Scripts\Activate.ps1
uvicorn pcb_ai_api.main:app --reload --app-dir apps/api/src
```

Leave this terminal running. Health check:

```powershell
curl http://127.0.0.1:8000/health
```

### 2. Install the plugin

```powershell
cd C:\Users\adars\Documents\PCB_Copilot
.\scripts\install_kicad_plugin.ps1
```

Typical install target (KiCad creates a versioned config tree):

- `%APPDATA%\kicad\10.0\scripting\plugins\pcb_copilot_layout\`
- or `%APPDATA%\kicad\scripting\plugins\pcb_copilot_layout\`

Confirm in the PCB editor Python console if needed:

```python
import pcbnew
print(pcbnew.PLUGIN_DIRECTORIES_SEARCH)
```

### 3. Open a small project in KiCad

Use the repo fixture schematic. Easiest path for MVP:

1. Copy `tests\fixtures\kicad\rc_divider.kicad_sch` into a working folder (optional but keeps fixtures clean), **or** open it in place.
2. In KiCad: create a new PCB for that project / open an existing `.kicad_pcb` next to the schematic (same stem), **save the board to disk**.
3. The plugin needs a real board file path (`BOARD().GetFileName()`) and a sibling `*.kicad_sch`.

Example layout on disk:

```text
C:\temp\rc_divider\
  rc_divider.kicad_sch
  rc_divider.kicad_pcb   ← open this in PCB editor (can be empty/minimal)
```

### 4. Run the action

In the **PCB editor**:

**Tools → External Plugins → PCB Copilot — AI Layout**

(or the toolbar button if shown)

1. Wait for the API layout response.
2. Read the summary dialog (`proposal_id`, unrouted nets, finding counts).
3. Click **Approve** → writes `rc_divider-copilot.kicad_pcb` next to the board and tries to open it.
4. Or **Reject** → nothing written.

Production `rc_divider.kicad_pcb` is never overwritten.

### 5. Optional API smoke (without KiCad)

```powershell
curl -Method POST `
  -Form "file=@tests/fixtures/kicad/rc_divider.kicad_sch" `
  -Form "pcb_name=rc_divider-copilot.kicad_pcb" `
  -Form "register_proposal=true" `
  http://127.0.0.1:8000/v1/layout
```

Approve decision (replace `{proposal_id}`):

```powershell
curl -Method POST `
  -ContentType "application/json" `
  -Body '{"decision":"approve","reason":"manual smoke"}' `
  http://127.0.0.1:8000/v1/proposals/{proposal_id}/decision
```

## Configuration

| Source | Key |
|--------|-----|
| Env | `PCB_COPILOT_API_BASE` (preferred) or `PCB_AI_API_BASE` |
| Env | `PCB_COPILOT_TIMEOUT_S` (seconds, default 120) |
| File | `pcb_copilot_settings.json` next to the installed plugin, or `%APPDATA%\pcb-copilot\settings.json` |

Example settings file (also `pcb_copilot_settings.example.json` in this folder):

```json
{
  "api_base": "http://127.0.0.1:8000",
  "timeout_s": 120
}
```

## Package layout

```text
apps/kicad-plugin/
  README.md
  pcb_copilot_settings.example.json
  pcb_copilot_layout/
    __init__.py      # registers ActionPlugin inside KiCad
    action.py        # Run() orchestration
    api_client.py    # stdlib HTTP multipart + decision POST
    config.py        # API base / timeout
    dialog.py        # wx summary Approve/Reject
    paths.py         # board → schematic + sidecar write guards
scripts/install_kicad_plugin.ps1
```

## Guardrails

- Sidecar name is always `*-copilot.kicad_pcb`.
- Writes refuse any target that would replace a non-`-copilot` production board.
- Layout uses `POST /v1/layout` (not production CAD mutation; API returns `production_mutation: false`).

## Known MVP limitations

- PCB editor only (no schematic-editor action yet).
- Reloading the sidecar into the *same* PCB editor session is best-effort (`os.startfile` / File → Open); KiCad may open a second window.
- Requires a saved board path and a discoverable sibling `.kicad_sch`.
- API must be reachable on localhost; no auth.
- Grid placer/router MVP: small boards (≤~20 footprints); expect unrouted nets on harder nets.
