$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== DronePanoRAW 360 (DPR360) · setup Windows ===" -ForegroundColor Cyan
Write-Host "Directory: $PSScriptRoot"

$py = $null
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $py = "py"; $pyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
else {
  Write-Host "Python 3 non trovato. Installalo e rilancia setup.bat." -ForegroundColor Red
  exit 2
}

if (-not (Test-Path ".venv")) {
  Write-Host "Creo ambiente virtuale..."
  & $py @pyArgs -m venv .venv
}
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
Write-Host "Setup Python completato." -ForegroundColor Green

Write-Host "Rilevo/installo le dipendenze esterne in modo indipendente..." -ForegroundColor Cyan
try { & $venvPython installer_cli.py --auto }
catch { Write-Host "Setup tool esterni parziale: $($_.Exception.Message)" -ForegroundColor Yellow }

Write-Host ""
Write-Host "Setup terminato. Avvia run_dpr360.bat" -ForegroundColor Green
