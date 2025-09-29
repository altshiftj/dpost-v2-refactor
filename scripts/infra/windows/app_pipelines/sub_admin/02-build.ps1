. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# Simulate GitLab "build" job locally in PowerShell

# --- SETTINGS ---
$CI_JOB_NAME   = $env:CI_JOB_NAME
$CI_COMMIT_TAG = $env:CI_COMMIT_TAG
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = $env:COMMIT_TAG }
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = "vLocalTest" }

if (-not $CI_JOB_NAME)   { $CI_JOB_NAME = "deploy_test" }
if (-not $CI_COMMIT_TAG) { $CI_COMMIT_TAG = "vLocalTest" }

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Create Virtual Environment ---
if (!(Test-Path ".test_buildvenv")) {
    python -m venv .test_buildvenv
}

# --- Step 2: Activate Virtual Environment ---
. .\.test_buildvenv\Scripts\Activate.ps1
$python = ".\.test_buildvenv\Scripts\python.exe"

Write-Host "`nUpgrading pip/setuptools/wheel..."
& $python -m pip install --upgrade pip setuptools wheel

# --- Step 3: Derive PC_NAME from CI_JOB_NAME ---
$PC_NAME = $CI_JOB_NAME
$DEVICES = $env:DEVICE_NAMES -split ","
Write-Host "`nUsing PC: $PC_NAME"

# --- Step 4: Install build and device dependencies (no dev) ---
Write-Host "`nInstalling project with [build,$PC_NAME,$DEVICES] extras..."
& $python -m pip install -e .[build,$PC_NAME,$DEVICES]

# --- Step 5: Create environment and version files ---
Write-Host "`nCreating .env and version files..."

@"
COMMIT_TAG=$env:COMMIT_TAG
COMMIT_HASH=$env:COMMIT_HASH
GIT_BRANCH=$env:GIT_BRANCH
BUILD_TIME=$env:BUILD_TIME
"@ | Out-File -Encoding ascii version.txt -Force
Copy-Item -Force version.txt build/version.txt

# --- Step 5b: Create build/.env with runtime config ---
try {
    if (-not (Test-Path build)) {
        New-Item -ItemType Directory -Path build | Out-Null
    }

    $pcNameValue = if ($PC_NAME) { $PC_NAME } else { "unknown_pc" }
    # Prefer DEVICE_NAMES env var; fallback to joined $DEVICES; fallback to placeholder
    $devicePluginsValue = if ($env:DEVICE_NAMES) {
        $env:DEVICE_NAMES
    } elseif ($DEVICES -and $DEVICES.Count -gt 0 -and $DEVICES[0]) {
        ($DEVICES -join ",")
    } else {
        "unknown_device"
    }

    $buildEnvPath = "build/.env"
    @"
PC_NAME = $pcNameValue
DEVICE_PLUGINS = $devicePluginsValue
"@ | Out-File -Encoding ascii $buildEnvPath -Force

    Write-Host "Created ${buildEnvPath}:"
    Get-Content $buildEnvPath | ForEach-Object { "  $_" }
}
catch {
    Write-Warning "Failed to create build/.env: $($_.Exception.Message)"
}

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
