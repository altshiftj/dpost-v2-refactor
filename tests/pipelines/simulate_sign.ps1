# simulate_sign.ps1
# Simulate the GitLab CI "sign" stage locally using environment variables
# --- Load shared environment variables ---
. "$PSScriptRoot\env.ps1"

# --- SETTINGS ---
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
$ciJobName = $env:CI_JOB_NAME
if (-not $ciJobName) { $ciJobName = "run" }

$binaryName = "wd-${ciJobName}.exe"
$binaryPath = "C:\Repos\Gitlab\ipat_data_watchdog\dist\$binaryName"

$pfxPath  = $env:SIGNING_CERT_PFX
$pfxPass  = $env:SIGNING_CERT_PASS

# --- STEP 1: Validate inputs ---
if (!(Test-Path $signtool)) {
    Write-Error "signtool.exe not found. Install Windows SDK."
    exit 1
}

if (!(Test-Path $binaryPath)) {
    Write-Error "$binaryPath not found. Build the binary first."
    exit 1
}

if (-not $pfxPath -or !(Test-Path $pfxPath)) {
    Write-Error "SIGNING_CERT_PFX environment variable not set or path invalid."
    exit 1
}

if (-not $pfxPass) {
    Write-Error "SIGNING_CERT_PASS environment variable is missing."
    exit 1
}

# --- STEP 2: Sign the executable ---
Write-Host "Signing $binaryPath..."
& "$signtool" sign /f "$pfxPath" /p "$pfxPass" /tr http://timestamp.digicert.com `
    /td sha256 /fd sha256 "$binaryPath"

# --- STEP 3: Verfiy the .exe ---
Write-Host "Verifying $binaryPath..."
& "$signtool" verify /pa "$binaryPath"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Verification failed. Check the output above."
    exit 1
}

Write-Host "Signing successful."
