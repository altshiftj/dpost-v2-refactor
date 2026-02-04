# TODO: Implement error handling and logging
# TODO: Move away from passwords towards key-based authentication

function Get-ProjectRoot {
    param([string] $Start = $PSScriptRoot)

    $repoTop = $null
    try {
        $gitTop = (git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and $gitTop) {
            $repoTop = (Resolve-Path -LiteralPath $gitTop).Path
        }
    } catch {}

    $dir = Get-Item -LiteralPath $Start
    while ($dir) {
        $pp = Join-Path $dir.FullName 'pyproject.toml'
        if (Test-Path -LiteralPath $pp) { return $dir.FullName }

        if ($repoTop -and ((Resolve-Path -LiteralPath $dir.FullName).Path -ieq $repoTop)) { break }
        $dir = $dir.Parent
    }

    if ($repoTop -and (Test-Path -LiteralPath (Join-Path $repoTop 'pyproject.toml'))) {
        return $repoTop
    }

    throw "Could not locate project root (no pyproject.toml found)."
}

# Normalize and compose extras for pip installs based on CI job + device plugins.
function Get-PipExtras {
    param(
        [string]$CiJob,
        [string]$DevPlugins
    )
    $items = New-Object System.Collections.Generic.List[string]

    if ($CiJob) {
        $items.Add($CiJob.Trim()) | Out-Null
    }

    if ($DevPlugins) {
        ($DevPlugins -split '[,; ]+' | Where-Object { $_ -and $_.Trim().Length -gt 0 }) |
        ForEach-Object { $items.Add($_.Trim()) | Out-Null }
    }

    # de-dup while preserving order
    $seen = @{}
    $orderedUnique = foreach ($i in $items) {
        if (-not $seen.ContainsKey($i)) { $seen[$i] = $true; $i }
    }

    return ($orderedUnique -join ',')
}

# ------------------------------
# Project Root
# ------------------------------
if ($env:PROJECT_ROOT) {
    $pp = Join-Path $env:PROJECT_ROOT 'pyproject.toml'
    if (!(Test-Path -LiteralPath $pp)) {
        Write-Warning "Ignoring preset PROJECT_ROOT '$($env:PROJECT_ROOT)' (no pyproject.toml)."
        $env:PROJECT_ROOT = $null
    }
}

if (-not $env:PROJECT_ROOT) {
    $env:PROJECT_ROOT = Get-ProjectRoot
}
Write-Host "Project Root: $env:PROJECT_ROOT"

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
$env:CI_JOB_NAME = "zwick_blb"
$env:DEVICE_NAMES= "utm_zwick"
$env:DEVICE_PLUGINS = if ($env:DEVICE_PLUGINS) { $env:DEVICE_PLUGINS } else { $env:DEVICE_NAMES }
$env:PIP_EXTRAS = Get-PipExtras -CiJob $env:CI_JOB_NAME -DevPlugins $env:DEVICE_PLUGINS
$env:TARGET_IP   = "134.169.58.210"
$env:TARGET_USER = "admin"
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
