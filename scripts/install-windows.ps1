param(
  [switch]$Lan
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python 3.9+ is required."
}

$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not (Test-Path ".venv")) {
  & $Python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev,windows]"

Write-Host ""
Write-Host "NexPilot installed for Windows beta."
Write-Host "Run same-computer mode: .\.venv\Scripts\nexpilot.exe"
Write-Host "Run phone/LAN mode:     .\.venv\Scripts\nexpilot.exe --lan"

if ($Lan) {
  & ".\.venv\Scripts\nexpilot.exe" --lan
}
