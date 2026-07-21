# Build Protofluid Ada/SPARK binary
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$alr = (Get-Command alr -ErrorAction SilentlyContinue).Source
if (-not $alr) {
  $cand = @(
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\AdaLang.Alire.Portable_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\alr.exe",
    "$env:USERPROFILE\Desktop\Current work\video_llm\fsot_ada\alr.exe"
  )
  foreach ($c in $cand) {
    if (Test-Path $c) { $alr = $c; break }
  }
}
if (-not $alr) {
  Write-Error "alr not found. Install: winget install AdaLang.Alire"
}

Write-Host "Using alr: $alr" -ForegroundColor Cyan
& $alr --version
& $alr build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = Join-Path $PSScriptRoot "bin\pflt_ada.exe"
if (-not (Test-Path $exe)) {
  # Alire may put exe under bin/ or ./bin relative to crate
  $exe = Get-ChildItem -Path $PSScriptRoot -Recurse -Filter "pflt_ada.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
}
Write-Host "Running $exe" -ForegroundColor Green
& $exe
if ($args.Count -gt 0) {
  & $exe @args
}
