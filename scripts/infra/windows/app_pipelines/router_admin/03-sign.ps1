<#
    Simulate GitLab "sign" stage with router-based environment:
    - Signs the built executable with code signing certificate
#>
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

Write-Host "== Simulating SIGN stage (Router-based pipeline) =="

# ── SETTINGS ────────────────────────────────
$ciJobName = $env:CI_JOB_NAME
$binaryName = "wd-$ciJobName.exe"
$distPath = "dist\$binaryName"
$certPath = $env:SIGNING_CERT_PFX
$certPass = $env:SIGNING_CERT_PASS

# ── VALIDATION ──────────────────────────────
if (!(Test-Path $distPath)) {
    Write-Error "Executable not found: $distPath (run build stage first)"
    exit 1
}

if (!(Test-Path $certPath)) {
    Write-Error "Certificate file not found: $certPath"
    exit 1
}

if (-not $certPass) {
    Write-Error "Certificate password not found in environment (SIGNING_CERT_PASS)"
    exit 1
}

# ── CHECK SIGNTOOL ──────────────────────────
$signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signTool) {
    Write-Error "signtool.exe not found. Install Windows SDK or add to PATH."
    exit 1
}

# ── SIGN EXECUTABLE ─────────────────────────
Write-Host "Signing executable: $distPath"
Write-Host "Using certificate: $certPath"

$signArgs = @(
    'sign',
    '/f', $certPath,
    '/p', $certPass,
    '/t', 'http://timestamp.digicert.com',  # Timestamp server
    '/fd', 'SHA256',                        # File digest algorithm
    '/v',                                   # Verbose output
    $distPath
)

& signtool.exe @signArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Code signing failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# ── VERIFY SIGNATURE ────────────────────────
Write-Host "`nVerifying signature..."
& signtool.exe verify /pa /v $distPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nCode signing successful!"
    
    # Show certificate info
    $cert = Get-AuthenticodeSignature $distPath
    Write-Host "Certificate Subject: $($cert.SignerCertificate.Subject)"
    Write-Host "Certificate Thumbprint: $($cert.SignerCertificate.Thumbprint)"
    Write-Host "Signature Status: $($cert.Status)"
} else {
    Write-Error "Signature verification failed"
    exit 1
}
