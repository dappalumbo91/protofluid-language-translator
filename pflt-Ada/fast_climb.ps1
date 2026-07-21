# Fast partial climb — seconds/minutes, not multi-hour full-corpus scans.
# Usage:
#   .\fast_climb.ps1              # supervised stems + neighbor + Ada eval
#   .\fast_climb.ps1 -NoBuild     # skip alr build
#   .\fast_climb.ps1 -Target 0.75

param(
    [double]$Target = 0.70,
    [switch]$NoBuild,
    [switch]$NoSupervised
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== FAST CLIMB (target partial=$Target) ===" -ForegroundColor Cyan
$sw = [System.Diagnostics.Stopwatch]::StartNew()

$args = @("--target", "$Target", "--neighbor-rounds", "2")
if ($NoSupervised) { $args += "--no-supervised-stems" }

python -u fast_climb.py @args
if ($LASTEXITCODE -ne 0) { throw "fast_climb.py failed" }

if (-not $NoBuild) {
    Write-Host "Building Ada..." -ForegroundColor Cyan
    alr build 2>&1 | Select-String -Pattern "error:|Success|failed"
}

Write-Host "OPEN-SET eval..." -ForegroundColor Cyan
.\bin\pflt_main.exe eval 2>&1 | Select-String -Pattern "===|partial|exact_rate|store|Goal|n="

Write-Host "PRODUCT eval..." -ForegroundColor Cyan
.\bin\pflt_main.exe eval-product 2>&1 | Select-String -Pattern "===|partial|exact_rate|store|Goal|n="

$sw.Stop()
Write-Host "Total wall time: $($sw.Elapsed.TotalSeconds.ToString('0.0'))s" -ForegroundColor Green
