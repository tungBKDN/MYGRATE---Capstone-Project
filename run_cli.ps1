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
} else {
    Write-Warning "Virtual environment folder (.venv or venv) not found. Running with standard python."
}

# Run the interactive CLI python application
python (Join-Path $ScriptDir "cli_app.py") $args
