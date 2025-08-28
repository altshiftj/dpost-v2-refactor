<#
    Simulate GitLab "build" stage with router-based environment:
    - Sets up virtual environment (.buildvenv)
    - Installs project dependencies
    - Runs PyInstaller to create executable
#>
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

Write-Host "== Simulating BUILD stage (Router-based pipeline) =="

# ── SETTINGS ────────────────────────────────
$venv = ".build_routervenv"
$python = ".\$venv\Scripts\python.exe"
$activate = ".\$venv\Scripts\Activate.ps1"
$ciJobName = $env:CI_JOB_NAME
$binaryName = "wd-$ciJobName.exe"

# ── CLEANUP ─────────────────────────────────
foreach ($path in @($venv, "dist", "build")) {
    if (Test-Path $path) {
        Write-Host "Removing existing $path..."
        Remove-Item -Recurse -Force $path
    }
}

# ── SETUP VENV ──────────────────────────────
Write-Host "`nCreating virtual environment..."
python -m venv $venv
. $activate

Write-Host "Upgrading pip/setuptools/wheel..."
& $python -m pip install -U pip setuptools wheel

# ── INSTALL DEPENDENCIES ───────────────────
Write-Host "Installing project with build dependencies..."

$extras = @("build", $env:CI_JOB_NAME)
$pipTarget = Get-PipInstallTarget -Extras $extras
Write-Host "pip install target: $pipTarget"
& $python -m pip install -e $pipTarget

# ── BUILD EXECUTABLE ───────────────────────
Write-Host "`n== Building executable with PyInstaller =="

$specFile = "build\specs\$ciJobName.spec"
if (!(Test-Path $specFile)) {
    Write-Error "PyInstaller spec file not found: $specFile"
    exit 1
}

& $python -m PyInstaller --clean --noconfirm $specFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# ── VERIFY BUILD OUTPUT ────────────────────
$distPath = "dist\$binaryName"
if (!(Test-Path $distPath)) {
    Write-Error "Expected executable not found: $distPath"
    exit 1
}

$fileSize = (Get-Item $distPath).Length
Write-Host "`nBuild successful:"
Write-Host "  Executable: $distPath"
Write-Host "  Size: $([math]::Round($fileSize / 1MB, 2)) MB"

# ── CREATE VERSION FILE ────────────────────
$versionContent = @"
COMMIT_TAG=$env:COMMIT_TAG
COMMIT_HASH=$env:COMMIT_HASH
GIT_BRANCH=$env:GIT_BRANCH
BUILD_TIME=$env:BUILD_TIME
"@

$versionContent | Set-Content -Encoding UTF8 "version.txt"
Write-Host "Created version.txt with build metadata"
