. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# Simulate GitLab "build" job locally in PowerShell

# --- SETTINGS ---
$CI_JOB_NAME   = $env:CI_JOB_NAME
$CI_COMMIT_TAG = $env:CI_COMMIT_TAG
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = $env:COMMIT_TAG }
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = "vLocalTest" }

if (-not $CI_JOB_NAME)   { $CI_JOB_NAME = "tischrem_blb" }
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = "vLocalTest" }

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Create Virtual Environment ---
if (!(Test-Path ".test_buildvenv")) {
    python -m venv .test_buildvenv
}

# --- Step 2: Activate Virtual Environment ---
.\.test_buildvenv\Scripts\Activate.ps1
$python = ".\.test_buildvenv\Scripts\python.exe"

Write-Host "`nUpgrading pip/setuptools/wheel..."
& $python -m pip install --upgrade pip setuptools wheel

# --- Step 3: Derive PC_NAME from CI_JOB_NAME ---
$PC_NAME = $CI_JOB_NAME
Write-Host "`nUsing PC_NAME: $PC_NAME"

# --- Step 4: Get devices for this PC and install dependencies ---
$devices = & $python -c "from ipat_watchdog.loader import get_devices_for_pc; print(','.join(get_devices_for_pc('$PC_NAME')))"
$deviceExtras = $devices -split ',' | ForEach-Object { $_.Trim() }
$allExtras = @('build') + $deviceExtras + @($PC_NAME)

Write-Host "`nInstalling project with extras: $($allExtras -join ',')"
& $python -m pip install -e ".[$($allExtras -join ',')]"

# --- Step 5: Create version file ---
Write-Host "`nCreating version file..."

@"
COMMIT_TAG=$env:COMMIT_TAG
COMMIT_HASH=$env:COMMIT_HASH
GIT_BRANCH=$env:GIT_BRANCH
BUILD_TIME=$env:BUILD_TIME
"@ | Out-File -Encoding ascii version.txt -Force
Copy-Item -Force version.txt build/version.txt

# --- Step 6: Build Executable ---
$specFile = "build/specs/$CI_JOB_NAME.spec"
Write-Host "`nRunning PyInstaller using spec file: $specFile"
$env:PYTHONPATH = "$(Get-Location)\src"
pyinstaller $specFile --clean --noconfirm

# --- Step 7: Check Result ---
$outputPath = "dist/wd-$CI_JOB_NAME.exe"
if (Test-Path $outputPath) {
    Write-Host "`nBuild succeeded. Executable: $outputPath"
} else {
    Write-Error "`nBuild failed. Expected output not found: $outputPath"
    exit 1
}

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "`nBuild simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
