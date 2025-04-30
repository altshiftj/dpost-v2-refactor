<#
    create_signing_cert.ps1
    ------------------------
    Developer-side script to generate and export a self-signed code-signing certificate
    for internal use with the IPAT-Watchdog application.

    • Creates a new self-signed certificate valid for 2 years
    • Exports a .pfx (with private key) for CI/CD code signing
    • Exports a .cer (public cert) for distribution and trust installation on devices
    • Output path: $env:USERPROFILE\certs
#>

# ─────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────
$certDir  = "$env:USERPROFILE\certs"
$pfxPath  = "$certDir\ipat_watchdog_signing.pfx"
$cerPath  = "$certDir\ipat_watchdog_signing.cer"
$subject  = "CN=IPAT Watchdog"

# Prompt user for password
$pfxPass1 = Read-Host -Prompt "Enter password to protect the .pfx file" -AsSecureString
$pfxPass2 = Read-Host -Prompt "Confirm password" -AsSecureString

if (-not (ConvertFrom-SecureString $pfxPass1) -eq (ConvertFrom-SecureString $pfxPass2)) {
    Write-Error "Passwords do not match. Exiting."
    exit 1
}

# ─────────────────────────────────────────────
# Create output directory
# ─────────────────────────────────────────────
if (-Not (Test-Path $certDir)) {
    New-Item -Path $certDir -ItemType Directory -Force | Out-Null
}

# ─────────────────────────────────────────────
# Create the self-signed certificate
# ─────────────────────────────────────────────
Write-Host "`nCreating self-signed code-signing certificate for '$subject'..."
$cert = New-SelfSignedCertificate `
    -Subject $subject `
    -KeyExportPolicy Exportable `
    -CertStoreLocation "Cert:\\CurrentUser\\My" `
    -Type CodeSigningCert `
    -NotAfter (Get-Date).AddYears(2)

# ─────────────────────────────────────────────
# Export the private key (.pfx) and public cert (.cer)
# ─────────────────────────────────────────────
Export-PfxCertificate -Cert $cert `
    -FilePath $pfxPath `
    -Password $pfxPass1

Export-Certificate -Cert $cert -FilePath $cerPath

Write-Host "`n[+] Certificate and keys exported to: $certDir"
Write-Host "[+] Private key (.pfx) for signing: $pfxPath"
Write-Host "[+] Public cert (.cer) for trusting: $cerPath"
