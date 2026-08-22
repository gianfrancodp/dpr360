$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== DronePanoRAW 360 (DPR360) · setup Windows ===" -ForegroundColor Cyan
Write-Host "Directory: $PSScriptRoot"

function Get-PythonInfo {
  param([string]$Executable, [string[]]$CommandArguments)
  $probe = "import json,sys; print(json.dumps({'executable':sys.executable,'major':sys.version_info.major,'minor':sys.version_info.minor,'micro':sys.version_info.micro,'releaselevel':sys.version_info.releaselevel,'version':sys.version.split()[0]}))"
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = & $Executable @CommandArguments -c $probe 2>$null
    $exitCode = $LASTEXITCODE
  }
  catch { return $null }
  finally { $ErrorActionPreference = $previousErrorActionPreference }
  if ($exitCode -ne 0 -or -not $output) { return $null }
  try { return ($output | Select-Object -Last 1 | ConvertFrom-Json) }
  catch { return $null }
}

$pythonCandidates = @(
  [pscustomobject]@{ Command = "py"; Arguments = @("-3.13") },
  [pscustomobject]@{ Command = "py"; Arguments = @("-3.12") },
  [pscustomobject]@{ Command = "py"; Arguments = @("-3.11") },
  [pscustomobject]@{ Command = "python"; Arguments = @() }
)
$selected = $null
$prerelease = $null
foreach ($candidate in $pythonCandidates) {
  if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) { continue }
  $info = Get-PythonInfo -Executable $candidate.Command -CommandArguments @($candidate.Arguments)
  if (-not $info) { continue }
  if ($info.major -lt 3 -or ($info.major -eq 3 -and $info.minor -lt 11)) { continue }
  $result = [pscustomobject]@{ Command = $candidate.Command; Arguments = $candidate.Arguments; Info = $info }
  if ($info.releaselevel -eq "final") { $selected = $result; break }
  if (-not $prerelease) { $prerelease = $result }
}
if (-not $selected) { $selected = $prerelease }
if (-not $selected) {
  Write-Host "Python 3.11 o superiore non trovato. Installa una versione stabile e rilancia setup.bat." -ForegroundColor Red
  exit 2
}
if ($selected.Info.releaselevel -ne "final") {
  Write-Host "Attenzione: uso Python prerelease $($selected.Info.version). È consigliata una release stabile." -ForegroundColor Yellow
}
Write-Host "Python: $($selected.Info.executable) · $($selected.Info.version)"

if (-not (Test-Path ".venv")) {
  Write-Host "Creo ambiente virtuale..."
  & $selected.Command @($selected.Arguments) -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw "Creazione ambiente virtuale fallita (exit code $LASTEXITCODE)." }
}
$venvPython = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
if (-not (Test-Path $venvPython)) { throw "Ambiente virtuale non valido: $venvPython non trovato." }
& $venvPython -c "import sys; assert sys.version_info >= (3, 11)"
if ($LASTEXITCODE -ne 0) { throw "L'ambiente virtuale richiede Python 3.11 o superiore." }

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Aggiornamento pip fallito (exit code $LASTEXITCODE)." }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Installazione dipendenze Python fallita (exit code $LASTEXITCODE)." }
Write-Host "Setup Python completato." -ForegroundColor Green

Write-Host "Rilevo/installo le dipendenze esterne in modo indipendente..." -ForegroundColor Cyan
& $venvPython installer_cli.py --auto
$installerExit = $LASTEXITCODE
if ($installerExit -ne 0) {
  Write-Host "Setup tool esterni parziale (exit code $installerExit)." -ForegroundColor Yellow
  exit $installerExit
}

Write-Host ""
Write-Host "Setup terminato. Avvia run_dpr360.bat" -ForegroundColor Green
exit 0
