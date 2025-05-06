. "$PSScriptRoot/env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

# simulate_build.ps1
# Simulate GitLab "build" job locally in PowerShell

# --- SETTINGS ---

# Fallbacks for environment variables if not set externally
$CI_JOB_NAME   = $env:CI_JOB_NAME
$CI_COMMIT_TAG = $env:CI_COMMIT_TAG

if (-not $CI_JOB_NAME)   { $CI_JOB_NAME = "sem_tischrem_blb" }
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = "vLocalTest" }

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Create Virtual Environment ---
if (!(Test-Path ".testbuildvenv")) {
    python -m venv .testbuildvenv
}

# --- Step 2: Activate Virtual Environment ---
. .\.testbuildvenv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel pyinstaller

# --- Step 3: Derive DEVICE_NAME from CI_JOB_NAME ---
$DEVICE_NAME = $CI_JOB_NAME
Write-Host "Using DEVICE_NAME: $DEVICE_NAME"

# --- Step 4: Install Project Dependencies ---
$pipTarget = Get-PipInstallTarget -Extras @("dev", $DEVICE_NAME)
Write-Host "Installing dependencies using: $pipTarget"
pip install --cache-dir .cache/pip -e $pipTarget

# --- Step 5: Create environment and version files ---
Write-Host "Creating .env and version files..."
"DEVICE_NAME=$DEVICE_NAME" | Out-File -Encoding ascii device.env -Force
Copy-Item -Force device.env build/.env

$CI_COMMIT_TAG | Out-File -Encoding ascii version.txt -Force
Copy-Item -Force version.txt build/version.txt

# --- Step 6: Build Executable ---
$specFile = "build/specs/$CI_JOB_NAME.spec"
Write-Host "Running PyInstaller using spec file: $specFile"
$env:PYTHONPATH = "$(Get-Location)\src"
pyinstaller $specFile --clean --noconfirm

# --- Step 7: Check Result ---
$outputPath = "dist/wd-$CI_JOB_NAME.exe"
if (Test-Path $outputPath) {
    Write-Host "Build succeeded. Executable: $outputPath"
} else {
    Write-Error "Build failed. Expected output not found: $outputPath"
    exit 1
}

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "Build simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
