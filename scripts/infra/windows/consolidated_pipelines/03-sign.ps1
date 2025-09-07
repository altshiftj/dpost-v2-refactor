<# ========================= 03-sign.ps1 =========================
Purpose:
- Unified code signing script for all configurations
- Signs the built executable with digital certificate
- Validates signature after signing
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin"
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up signing environment"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    Write-PipelineStep "VALIDATION" "Checking build artifacts"
    
    # Verify build artifacts exist
    $artifacts = Test-BuildArtifacts -ProjectRoot $env:PROJECT_ROOT -JobName $env:CI_JOB_NAME
    
    Write-PipelineStep "CERTIFICATE" "Validating signing certificate"
    
    # Check certificate and password
    if (-not $env:SIGNING_CERT_PFX -or -not (Test-Path $env:SIGNING_CERT_PFX)) {
        Write-PipelineError "CERTIFICATE" "Signing certificate not found: $env:SIGNING_CERT_PFX" 1
    }
    
    if (-not $env:SIGNING_CERT_PASS) {
        Write-PipelineError "CERTIFICATE" "Signing certificate password not available" 1
    }
    
    Write-Host "Certificate: $env:SIGNING_CERT_PFX"
    Write-Host "Target binary: $($artifacts.BinaryPath)"
    
    # Check if signtool is available
    $signTool = Get-Command signtool -ErrorAction SilentlyContinue
    if (-not $signTool) {
        Write-PipelineError "CERTIFICATE" "signtool.exe not found. Install Windows SDK or Visual Studio Build Tools" 1
    }
    
    Write-PipelineStep "SIGNING" "Digitally signing executable"
    
    # Sign the executable
    $signArgs = @(
        "sign"
        "/f", $env:SIGNING_CERT_PFX
        "/p", $env:SIGNING_CERT_PASS
        "/t", "http://timestamp.digicert.com"  # Timestamp server
        "/fd", "SHA256"  # File digest algorithm
        "/v"  # Verbose output
        $artifacts.BinaryPath
    )
    
    Write-Host "Running signtool..."
    & signtool @signArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "SIGNING" "Code signing failed with exit code $LASTEXITCODE" $LASTEXITCODE
    }
    
    Write-PipelineStep "VERIFICATION" "Verifying digital signature"
    
    # Verify the signature
    $verifyArgs = @(
        "verify"
        "/pa"  # Use default authentication verification policy
        "/v"   # Verbose output
        $artifacts.BinaryPath
    )
    
    & signtool @verifyArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "VERIFICATION" "Signature verification failed with exit code $LASTEXITCODE" $LASTEXITCODE
    }
    
    Write-Host "`nExecutable successfully signed and verified." -ForegroundColor Green
    
    # Display signature info using PowerShell
    try {
        $signature = Get-AuthenticodeSignature $artifacts.BinaryPath
        Write-Host "`nSignature Details:"
        Write-Host "  Status: $($signature.Status)"
        Write-Host "  Subject: $($signature.SignerCertificate.Subject)"
        Write-Host "  Thumbprint: $($signature.SignerCertificate.Thumbprint)"
        Write-Host "  Valid From: $($signature.SignerCertificate.NotBefore)"
        Write-Host "  Valid To: $($signature.SignerCertificate.NotAfter)"
        
        if ($signature.TimeStamperCertificate) {
            Write-Host "  Timestamp: $($signature.TimeStamperCertificate.Subject)"
        }
    } catch {
        Write-Warning "Could not retrieve detailed signature information: $($_.Exception.Message)"
    }
    
} catch {
    Write-PipelineError "SIGNING" "Signing failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
}

Write-Host "`nSigning pipeline completed successfully." -ForegroundColor Green
