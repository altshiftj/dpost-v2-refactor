# Automatically extract detailed Git metadata
try {
    $commitTag = git describe --tags --always
    $branchName = git rev-parse --abbrev-ref HEAD
    $commitHash = git rev-parse HEAD
    $buildTime = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

    $env:COMMIT_TAG = $commitTag
    $env:GIT_BRANCH = $branchName
    $env:COMMIT_HASH = $commitHash
    $env:BUILD_TIME = $buildTime

    Write-Host "Using Commit Tag: $commitTag"
    Write-Host "Branch: $branchName"
    Write-Host "Commit Hash: $commitHash"
    Write-Host "Build Time: $buildTime"
} catch {
    Write-Warning "Git not found or not a Git repository."
}

# ------------------------------
# CI-related Defaults
# ------------------------------
$env:CI_JOB_NAME = "utm_zwick_blb"
$env:TARGET_IP   = "134.169.58.131"
$env:TARGET_USER = "messrechner"
$env:SSH_PORT    = 22

# ------------------------------
# Certificates & Secure Passwords
# ------------------------------
$env:SIGNING_CERT_PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"

$pfxPassPath     = "$env:USERPROFILE\.secure\pfxpass.txt"
$targetPassPath  = "$env:USERPROFILE\.secure\$env:CI_JOB_NAME.txt"

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
# SSH Tunneling for Local Access
# ------------------------------
$env:TUN_PORT_0 = 8000     # Local forward to remote 8000
$env:TUN_PORT_1 = 8001     # Local forward to remote 8001

# Optional: Add SSH host key fingerprint to prevent MITM (man in the middle) prompt
$env:SSH_HOSTKEY = 'AAAAC3NzaC1lZDI1NTE5AAAAIEaXU0p4npXkadBZ0RSBVFeaMg3HtUmErmEJo7kj+gR9'

# ------------------------------
# Paths
# ------------------------------
$env:REMOTE_DIR     = "C:\Watchdog"

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
