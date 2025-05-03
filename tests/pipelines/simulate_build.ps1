# simulate_build.ps1
# Simulate your GitLab "build" job locally in PowerShell

# --- SETTINGS ---
$pythonExe = "C:\Program Files\Python312\python.exe"
$commitTag = "vLocalTest"  # Simulate CI_COMMIT_TAG

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Check Python ---
if (-Not (Test-Path $pythonExe)) {
    Write-Error "$pythonExe not found. Please install Python 3.12 or adjust path." # -ForegroundColor Red
    exit 1
}
Write-Host "Using $pythonExe" # -ForegroundColor Green

# --- Step 2: Create Virtual Environment ---
& $pythonExe -m venv .build-venv

# --- Step 3: Activate Virtual Environment ---
. .\.build-venv\Scripts\Activate.ps1

# --- Step 4: Install Dependencies ---
Write-Host "Installing dependencies..." # -ForegroundColor Yellow
pip install --cache-dir .cache/pip -r requirements.txt
pip install --cache-dir .cache/pip pyinstaller python-dotenv

# --- Step 5: Mock Environment Variables ---
Write-Host "Setting up mock environment variables..." # -ForegroundColor Yellow
$env:DEVICE_NAME = "SEM_TischREM_BLB"

# Create .env for consistency
"DEVICE_NAME=$($env:DEVICE_NAME)" | Out-File -Encoding ascii .env -Force
Copy-Item -Force .env build/.env

# Simulate GitLab version tag
$commitTag | Out-File -Encoding ascii version.txt -Force
Copy-Item -Force version.txt build/version.txt

# --- Step 6: Build Executable ---
Write-Host "Running PyInstaller..." # -ForegroundColor Yellow
$env:PYTHONPATH = "$(Get-Location)\src"
pyinstaller build/run.spec

# --- Step 7: Check Result ---
if (Test-Path dist/run.exe) {
    Write-Host "Build succeeded! run.exe available in dist/" # -ForegroundColor Green
} else {
    Write-Error "Build failed! dist/run.exe was not created." # -ForegroundColor Red
    exit 1
}

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "Build simulation complete!" # -ForegroundColor Green
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration) # -ForegroundColor Green
