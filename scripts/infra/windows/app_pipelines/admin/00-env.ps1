<# ========================= 00-env.ps1 =========================
Purpose:
- Export common environment variables for pipelines and local scripts
- Detect and expose $env:PROJECT_ROOT pointing at the repo root (with pyproject.toml)
- Collect Git metadata (tag/branch/commit/time)
- Provide CI defaults, secure secret loading, SSH config, and helpers
================================================================ #>

# ------------------------------
# Utilities
# ------------------------------

function Get-ProjectRoot {
    param(
        [string] $Start = $PSScriptRoot
    )

    # Find repo boundary if possible (folder containing .git)
    $repoTop = $null
    try {
        $gitTop = (git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and $gitTop) {
            $repoTop = (Resolve-Path -LiteralPath $gitTop).Path
        }
    } catch {}

    # Walk upward starting at $Start, but do not go above $repoTop (if known)
    $dir = Get-Item -LiteralPath $Start
    while ($dir) {
        $pp = Join-Path $dir.FullName 'pyproject.toml'
        if (Test-Path -LiteralPath $pp) {
            return $dir.FullName
        }

        # If we know repoTop, stop once we reach it (after checking it)
        if ($repoTop -and ((Resolve-Path -LiteralPath $dir.FullName).Path -ieq $repoTop)) {
            break
        }
        $dir = $dir.Parent
    }

    # If we know repoTop, as a last try, accept it if it has pyproject.toml
    if ($repoTop -and (Test-Path -LiteralPath (Join-Path $repoTop 'pyproject.toml'))) {
        return $repoTop
    }

    throw "Could not locate project root (no pyproject.toml found; start='$Start', repoTop='$repoTop')."
}

# ------------------------------
# Project Root
# ------------------------------
# Accept a pre-set PROJECT_ROOT only if it contains a pyproject.toml
$needDetect = $true
if ($env:PROJECT_ROOT) {
    $pp = Join-Path $env:PROJECT_ROOT 'pyproject.toml'
    if ((Test-Path -LiteralPath $env:PROJECT_ROOT) -and (Test-Path -LiteralPath $pp)) {
        $needDetect = $false
    } else {
        Write-Warning "Ignoring preset PROJECT_ROOT '$($env:PROJECT_ROOT)' (no pyproject.toml found there)."
    }
}

if ($needDetect) {
    try {
        $env:PROJECT_ROOT = Get-ProjectRoot
    } catch {
        Write-Warning $_.Exception.Message
        throw  # Fail fast instead of silently picking a wrong parent like D:\Repos
    }
}

Write-Host "Project Root: $env:PROJECT_ROOT"


# ------------------------------
# Git Metadata (best-effort)
# ------------------------------
try {
    $commitTag  = git describe --tags --always
    $branchName = git rev-parse --abbrev-ref HEAD
    $commitHash = git rev-parse HEAD
    $buildTime  = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

    $env:COMMIT_TAG  = $commitTag
    $env:GIT_BRANCH  = $branchName
    $env:COMMIT_HASH = $commitHash
    $env:BUILD_TIME  = $buildTime

    Write-Host "Using Commit Tag: $commitTag"
    Write-Host "Branch: $branchName"
    Write-Host "Commit Hash: $commitHash"
    Write-Host "Build Time: $buildTime"
} catch {
    Write-Warning "Git not found or not a Git repository."
}

# ------------------------------
# CI-related Defaults (PC-centric)
# ------------------------------
$env:CI_JOB_NAME = "tischrem_blb"     # PC plugin name (was device name)
$env:TARGET_IP   = "134.169.58.85"   # Router's WAN IP
$env:TARGET_USER = "TischREM"
$env:SSH_PORT    = 22                # External SSH port

# ------------------------------
# Certificates & Secure Passwords
# ------------------------------
$env:SIGNING_CERT_PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"

$pfxPassPath    = Join-Path $env:USERPROFILE ".secure\pfxpass.txt"
$targetPassPath  = "$env:USERPROFILE\.secure\$env:CI_JOB_NAME.txt"

try {
    if (Test-Path -LiteralPath $pfxPassPath) {
        $securePfxPass = Get-Content $pfxPassPath | ConvertTo-SecureString
        $bstr1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePfxPass)
        $env:SIGNING_CERT_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr1)
    } else {
        Write-Warning "PFX password file not found: $pfxPassPath"
    }

    if (Test-Path -LiteralPath $targetPassPath) {
        $secureTargetPass = Get-Content $targetPassPath | ConvertTo-SecureString
        $bstr2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureTargetPass)
        $env:TARGET_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr2)
    } else {
        Write-Warning "Target password file not found: $targetPassPath"
    }
} catch {
    Write-Warning "Failed to load encrypted passwords. Check your .secure folder. ($($_.Exception.Message))"
}

# ------------------------------
# SSH Tunneling for Local Access
# ------------------------------
$env:TUN_PORT_0 = 8000     # Local forward to remote 8000
$env:TUN_PORT_1 = 8001     # Local forward to remote 8001

# Optional: Add SSH host key fingerprint to prevent MITM prompt
$env:SSH_HOSTKEY = 'ssh-ed25519 SHA256:P03FAAzlTdGcjLmBst8XNZ696VEzT1hq1sB2KDdejF4'

# ------------------------------
# Paths (derived where helpful)
# ------------------------------
$env:REMOTE_PATH = "C:\Watchdog"
$env:REMOTE_EXE  = "$env:REMOTE_PATH\wd-$env:CI_JOB_NAME.exe"  # Use PC-based naming

# ------------------------------
# Shared Helpers
# ------------------------------
function Get-PipInstallTarget {
    param (
        [string[]] $Extras
    )
    if (-not $Extras -or $Extras.Count -eq 0) { return "." }
    $joined = ($Extras -join ",")
    return ".[$joined]"
}

# ------------------------------
# Final Echo (handy when dot-sourcing)
# ------------------------------
Write-Host "Env loaded. CI_JOB_NAME='$($env:CI_JOB_NAME)' (PC plugin)  REMOTE_EXE='$($env:REMOTE_EXE)'"
