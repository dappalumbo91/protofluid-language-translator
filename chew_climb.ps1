# Launch autonomous PFLT climb (local only — no cloud APIs).
# Usage:
#   .\chew_climb.ps1
#   .\chew_climb.ps1 -Target 0.45 -MaxRounds 200
#   .\chew_climb.ps1 -Status
#   .\chew_climb.ps1 -Resume

param(
    [double]$Target = 0.40,
    [int]$MaxRounds = 100,
    [int]$Sample = 2500,
    [int]$FullEvery = 5,
    [ValidateSet("supervised","strict","oracle")]
    [string]$Mode = "supervised",
    [switch]$Resume,
    [switch]$Status,
    [switch]$Background
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Status) {
    python chew_climb.py --status
    exit $LASTEXITCODE
}

$args = @(
    "chew_climb.py",
    "--target", "$Target",
    "--max-rounds", "$MaxRounds",
    "--sample", "$Sample",
    "--full-every", "$FullEvery",
    "--mode", $Mode
)
if ($Resume) { $args += "--resume" }

Write-Host "PFLT chew_climb  target=$Target  rounds=$MaxRounds  mode=$Mode" -ForegroundColor Cyan
Write-Host "Logs: data\chew_climb\  |  Ctrl+C saves and exits" -ForegroundColor DarkGray

if ($Background) {
    $log = Join-Path $PSScriptRoot "data\chew_climb\daemon.log"
    New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
    Start-Process -FilePath "python" -ArgumentList $args -WorkingDirectory $PSScriptRoot `
        -RedirectStandardOutput $log -RedirectStandardError $log -WindowStyle Hidden
    Write-Host "Started background. Tail log: Get-Content '$log' -Wait -Tail 40"
    exit 0
}

python @args
exit $LASTEXITCODE
