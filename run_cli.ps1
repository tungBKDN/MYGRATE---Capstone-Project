# Get the directory of this script
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

# Define virtual environment paths
$VenvActivate = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
$VenvActivateFallback = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"

if (Test-Path $VenvActivate) {
    Write-Host "[MYGRATE] Activating virtual environment (.venv)..." -ForegroundColor Cyan
    . $VenvActivate
} elseif (Test-Path $VenvActivateFallback) {
    Write-Host "[MYGRATE] Activating virtual environment (venv)..." -ForegroundColor Cyan
    . $VenvActivateFallback
}

# Run the interactive CLI python application
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvPythonFallback = Join-Path $ScriptDir "venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython (Join-Path $ScriptDir "cli_app.py") $args
} elseif (Test-Path $VenvPythonFallback) {
    & $VenvPythonFallback (Join-Path $ScriptDir "cli_app.py") $args
} else {
    python (Join-Path $ScriptDir "cli_app.py") $args
}
