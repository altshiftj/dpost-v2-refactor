# simulate_sign.ps1
# Locally sign the executable using signtool on the runner

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# --- SETTINGS ---
$ciJobName  = $env:CI_JOB_NAME
$remotePfx  = $env:SIGNING_CERT_PFX -replace '/', '\\'
$remotePass = $env:SIGNING_CERT_PASS

$exePath = "dist/wd-${ciJobName}.exe"

# --- Validate tool and file ---
$signtoolCmd = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if (-not $signtoolCmd) {
    Write-Error "signtool.exe not found in PATH. Add Windows SDK bin folder to your environment variables."
    exit 1
}
$signtool = $signtoolCmd.Source

if (-not (Test-Path $exePath)) {
    Write-Error "Executable not found at $exePath"
    exit 1
}

# --- Sign ---
Write-Host "Signing $exePath..."
& $signtool sign /f "$remotePfx" /p "$remotePass" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "$exePath"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Signing failed."
    exit 1
}

# --- Verify ---
& $signtool verify /pa "$exePath"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Verification failed."
    exit 1
}
