# Install editable packages in dependency order (pip; uv workspace optional later).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install -U pip hatchling
python -m pip install -e packages/circuit-ir
python -m pip install -e packages/evidence -e packages/transactions -e packages/verification -e packages/kicad-adapter -e packages/agent -e packages/simulation -e packages/benchmarks -e packages/component-library
python -m pip install -e apps/api -e services/worker
python -m pip install pytest pytest-asyncio ruff httpx

Write-Host "Installed PCB Copilot packages."
