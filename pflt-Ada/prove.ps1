# Run GNATprove on SPARK units
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$alr = (Get-Command alr -ErrorAction SilentlyContinue).Source
if (-not $alr) {
  $alr = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\AdaLang.Alire.Portable_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\alr.exe"
}
if (Test-Path $alr) {
  & $alr gnatprove -- -P pflt_ada.gpr --level=2 --report=all
} else {
  gnatprove -P pflt_ada.gpr --level=2 --report=all
}
