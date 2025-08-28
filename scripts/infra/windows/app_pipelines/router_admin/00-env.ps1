<# ========================= 00-env.ps1 (Router + Admin, Tunnel Mode) =========================
Purpose:
- Export common environment variables for router-based pipelines
- Detect and expose $env:PROJECT_ROOT pointing at the repo root (with pyproject.toml)
- Collect Git metadata (tag/branch/commit/time)
- Provide router SSH config and Windows PC target config
- Support SSH tunneling through Linux router to Windows target PC (plink port forward)
=============================================================================================== #>

# ------------------------------
# Utilities
# ------------------------------

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

# ------------------------------
# Git Metadata (best-effort)
# ------------------------------
try {
    $env:COMMIT_TAG  = git describe --tags --always
    $env:GIT_BRANCH  = git rev-parse --abbrev-ref HEAD
    $env:COMMIT_HASH = git rev-parse HEAD
    $env:BUILD_TIME  = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

    Write-Host "Using Commit Tag: $env:COMMIT_TAG"
    Write-Host "Branch: $env:GIT_BRANCH"
    Write-Host "Commit Hash: $env:COMMIT_HASH"
    Write-Host "Build Time: $env:BUILD_TIME"
} catch {
    Write-Warning "Git not found or not a Git repository."
}

# ------------------------------
# CI-related Defaults
# ------------------------------
$env:CI_JOB_NAME = "sem_tischrem_blb"

# ------------------------------
# Router Configuration (Linux Jump Host)
# ------------------------------
$env:ROUTER_IP   = "134.169.58.199"
$env:ROUTER_USER = "ipat"
$env:ROUTER_PORT = 22

# ------------------------------
# Windows Target PC Configuration (Behind Router)
# ------------------------------
$env:TARGET_IP   = "192.168.1.2"
$env:TARGET_USER = "horiba"
$env:TARGET_PORT = 22

# Tunnel endpoint on local machine
$env:TARGET_TUNNEL_PORT = 2222

# ------------------------------
# Certificates & Secure Passwords
# ------------------------------
$env:SIGNING_CERT_PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"

$pfxPassPath    = Join-Path $env:USERPROFILE ".secure\pfxpass.txt"
$routerPassPath = "$env:USERPROFILE\.secure\misch_route.txt"
$targetPassPath = "$env:USERPROFILE\.secure\$env:CI_JOB_NAME.txt"

try {
    if (Test-Path -LiteralPath $pfxPassPath) {
        $securePfxPass = Get-Content $pfxPassPath | ConvertTo-SecureString
        $bstr1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePfxPass)
        $env:SIGNING_CERT_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr1)
    }
    if (Test-Path -LiteralPath $routerPassPath) {
        $secureRouterPass = Get-Content $routerPassPath | ConvertTo-SecureString
        $bstr2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureRouterPass)
        $env:ROUTER_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr2)
    }
    if (Test-Path -LiteralPath $targetPassPath) {
        $secureTargetPass = Get-Content $targetPassPath | ConvertTo-SecureString
        $bstr3 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureTargetPass)
        $env:TARGET_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr3)
    }
} catch {
    Write-Warning "Failed to load encrypted passwords. Check your .secure folder. ($($_.Exception.Message))"
}

# ------------------------------
# SSH Keys and Host Keys
# ------------------------------
# SSH private key files for authentication
$env:ROUTER_SSH_KEY = "$env:USERPROFILE\.ssh\id_rsa_jamfitz_ppk.ppk"
$env:TARGET_SSH_KEY = "$env:USERPROFILE\.ssh\id_rsa_jamfitz_ppk.ppk"  # Same key or different one

# SSH Host Keys (from ssh-keyscan)
$env:ROUTER_SSH_HOSTKEY = 'AAAAC3NzaC1lZDI1NTE5AAAAIFqvmR5Q0yi8vFlHQmPDmqSfapwMtuAKflpiUA9UpSUY'
$env:TARGET_SSH_HOSTKEY = 'AAAAC3NzaC1lZDI1NTE5AAAAIDnde8wPsHN7mxhOmEFyH2UFzAdpyBWCtgJ7hO/O1wWq'

# NOTE: Updated TARGET_SSH_HOSTKEY with actual ed25519 key from ssh-keyscan 192.168.1.2

# ------------------------------
# Paths
# ------------------------------
$env:REMOTE_PATH = "C:\Watchdog"
$env:REMOTE_EXE  = "$env:REMOTE_PATH\$env:CI_JOB_NAME.exe"

# ------------------------------
# Tunnel Helpers
# ------------------------------
function Start-TargetTunnel {
    $plinkArgs = @(
        "-batch", "-N",
        "-L", "$($env:TARGET_TUNNEL_PORT):$($env:TARGET_IP):$($env:TARGET_PORT)",
        "-P", $env:ROUTER_PORT,
        "-i", $env:ROUTER_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:ROUTER_SSH_HOSTKEY,
        "$env:ROUTER_USER@$env:ROUTER_IP"
    )
    Write-Host "Starting SSH tunnel on localhost:$($env:TARGET_TUNNEL_PORT) → $($env:TARGET_IP):$($env:TARGET_PORT)"
    Start-Process -FilePath plink.exe -ArgumentList $plinkArgs -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

function Invoke-TargetCommand {
    param([string]$Command)
    $plinkArgs = @(
        "-batch", "-P", $env:TARGET_TUNNEL_PORT,
        "-i", $env:TARGET_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:TARGET_SSH_HOSTKEY,
        "$env:TARGET_USER@127.0.0.1", $Command
    )
    & plink.exe @plinkArgs
    return $LASTEXITCODE
}

function Copy-FileViaTunnel {
    param([string]$LocalFile, [string]$RemoteFile)
    $scpArgs = @(
        "-batch", "-P", $env:TARGET_TUNNEL_PORT,
        "-i", $env:TARGET_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:TARGET_SSH_HOSTKEY,
        $LocalFile, "$($env:TARGET_USER)@127.0.0.1`:$RemoteFile"
    )
    & pscp.exe @scpArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed to copy $LocalFile" }
}

# ------------------------------
# Final Echo
# ------------------------------
Write-Host "Router-based env loaded:"
Write-Host "  CI_JOB_NAME='$($env:CI_JOB_NAME)'"
Write-Host "  ROUTER_IP='$($env:ROUTER_IP)'"
Write-Host "  TARGET_IP='$($env:TARGET_IP)'"
Write-Host "  TARGET_TUNNEL_PORT='$($env:TARGET_TUNNEL_PORT)'"
Write-Host "  REMOTE_EXE='$($env:REMOTE_EXE)'"
