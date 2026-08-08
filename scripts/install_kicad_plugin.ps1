# Install / update the PCB Copilot KiCad Action Plugin into the user plugins dir.
# Usage (from repo root):
#   .\scripts\install_kicad_plugin.ps1
#   .\scripts\install_kicad_plugin.ps1 -PluginsDir "C:\path\to\scripting\plugins"

[CmdletBinding()]
param(
    [string]$PluginsDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repoRoot "apps\kicad-plugin\pcb_copilot_layout"

if (-not (Test-Path -LiteralPath $src)) {
    throw "Plugin source not found: $src"
}

function Find-KiCadPluginsDir {
    $appData = $env:APPDATA
    if (-not $appData) {
        throw "APPDATA is not set; pass -PluginsDir explicitly."
    }
    $kicadRoot = Join-Path $appData "kicad"
    $candidates = @()

    # Versioned config trees (KiCad 6+ / 10): %APPDATA%\kicad\10.0\scripting\plugins
    if (Test-Path -LiteralPath $kicadRoot) {
        Get-ChildItem -LiteralPath $kicadRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                $candidates += (Join-Path $_.FullName "scripting\plugins")
            }
    }
    # Legacy / unversioned
    $candidates += (Join-Path $kicadRoot "scripting\plugins")

    foreach ($c in $candidates) {
        $parent = Split-Path -Parent $c
        if (Test-Path -LiteralPath $parent) {
            return $c
        }
    }
    # Default: create under highest-looking version or unversioned
    $ten = Join-Path $kicadRoot "10.0\scripting\plugins"
    if (Test-Path -LiteralPath (Join-Path $kicadRoot "10.0")) {
        return $ten
    }
    return (Join-Path $kicadRoot "scripting\plugins")
}

if (-not $PluginsDir) {
    $PluginsDir = Find-KiCadPluginsDir
}

New-Item -ItemType Directory -Force -Path $PluginsDir | Out-Null
$dest = Join-Path $PluginsDir "pcb_copilot_layout"

if (Test-Path -LiteralPath $dest) {
    Remove-Item -LiteralPath $dest -Recurse -Force
}

Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force

$exampleSettings = Join-Path $repoRoot "apps\kicad-plugin\pcb_copilot_settings.example.json"
$destSettings = Join-Path $dest "pcb_copilot_settings.json"
if ((Test-Path -LiteralPath $exampleSettings) -and -not (Test-Path -LiteralPath $destSettings)) {
    Copy-Item -LiteralPath $exampleSettings -Destination $destSettings
}

Write-Host "Installed PCB Copilot plugin to:"
Write-Host "  $dest"
Write-Host ""
Write-Host "Restart KiCad (or PCB editor), then: Tools → External Plugins → PCB Copilot — AI Layout"
Write-Host "API default: http://127.0.0.1:8000  (edit pcb_copilot_settings.json or set PCB_COPILOT_API_BASE)"
