# env.ps1

# Load CI-related values
$env:CI_JOB_NAME = "sem_tischrem_blb"
$env:TARGET_IP = "127.0.0.1"
$env:TARGET_USER = "testuser"

# .pfx certificate path
$env:SIGNING_CERT_PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"

# Secure password paths
$pfxPassPath = "$env:USERPROFILE\.secure\pfxpass.txt"
$targetPassPath = "$env:USERPROFILE\.secure\targetpass.txt"

# Read and decrypt passwords
try {
    $securePfxPass = Get-Content $pfxPassPath | ConvertTo-SecureString
    $bstr1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePfxPass)
    $env:SIGNING_CERT_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr1)
    $secureTargetPass = Get-Content $targetPassPath | ConvertTo-SecureString
    $bstr2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureTargetPass)
    $env:TARGET_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr2)
    } catch {
    Write-Warning "Failed to load encrypted passwords. Check your .secure folder."
}
