<#
    Simulate GitLab "test" stage:
    - Sets up virtual environment (.testbuildvenv)
    - Installs only test dependencies
    - Runs pytest
#>
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

Write-Host "== Simulating TEST stage =="

# ── SETTINGS ────────────────────────────────
$venv = ".test_testvenv"
$python = ".\$venv\Scripts\python.exe"
$activate = ".\$venv\Scripts\Activate.ps1"

# Optional cleanup
if (Test-Path $venv) {
    Remove-Item -Recurse -Force $venv
}

# ── SETUP VENV ──────────────────────────────
Write-Host "`nCreating virtual environment..."
python -m venv $venv
. $activate

Write-Host "Upgrading pip/setuptools/wheel..."
& $python -m pip install -U pip setuptools wheel

# install minimal test deps
Write-Host "Installing project with test dependencies..."

$extras = @("ci", $env:CI_JOB_NAME)
$pipTarget = Get-PipInstallTarget -Extras $extras
Write-Host "pip install target: $pipTarget"
& $python -m pip install -e $pipTarget

# ── RUN TESTS ───────────────────────────────
Write-Host "`n== Running pytest =="
& $python -m pytest tests/ --tb=short --disable-warnings --maxfail=5
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`nAll tests passed."
} else {
    Write-Error "`nTests failed with exit code $exitCode."
    exit $exitCode
}
