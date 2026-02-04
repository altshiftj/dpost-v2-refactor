<#
    Simulate GitLab "test" stage:
    - Sets up virtual environment (.testbuildvenv)
    - Installs only test dependencies
    - Runs pytest
#>
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

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

# ── INSTALL UNDER TEST WITH SELECTED EXTRAS ─
$extras = $env:PIP_EXTRAS
$pipTarget = if ([string]::IsNullOrWhiteSpace($extras)) { ".[ci]" } else { ".[$extras,ci]" }
Write-Host "Installing project for testing with extras: $pipTarget"
& $python -m pip install -e $pipTarget
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit $LASTEXITCODE }

# ── PREP ENV FOR TESTS ──────────────────────
# Main now reads ONLY build/.env in dev mode. Ensure it exists.
if (!(Test-Path "build")) { New-Item -ItemType Directory -Path "build" | Out-Null }
if (!(Test-Path "build\.env")) {
    Write-Host "Creating build\.env for tests (since main reads from build/.env)..."
    @"
PC_NAME=$($env:CI_JOB_NAME)
DEVICE_PLUGINS=$($env:DEVICE_PLUGINS)
"@ | Out-File -Encoding ascii build/.env -Force
}

# Also export PC_NAME for non-dotenv code paths (pure env-based)
$env:PC_NAME = $env:CI_JOB_NAME
# (DEVICE_PLUGINS is already in env from 00-env.ps1; leave as-is)

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
