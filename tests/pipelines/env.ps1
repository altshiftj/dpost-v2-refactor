# env.ps1

# ------------------------------
# CI-related Defaults
# ------------------------------
$env:CI_JOB_NAME = "sem_tischrem_blb"
$env:TARGET_IP = "134.169.58.176"
$env:TARGET_USER = "deploy"

# ------------------------------
# Certificates & Secure Passwords
# ------------------------------
$env:SIGNING_CERT_PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"

$pfxPassPath = "$env:USERPROFILE\.secure\pfxpass.txt"
$targetPassPath = "$env:USERPROFILE\.secure\targetpass.txt"

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

# ------------------------------
# Shared Functions
# ------------------------------

function Get-PipInstallTarget {
    param (
        [string[]] $Extras
    )
    $joined = ($Extras -join ",")
    return ".[$joined]"
}
