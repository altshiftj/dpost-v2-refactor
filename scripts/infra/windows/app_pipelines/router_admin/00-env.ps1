<# ========================= 00-env.ps1 (Router + Admin, Tunnel Mode) =========================
Purpose:
- Export common environment variables for router-based pipelines
- Detect and expose $env:PROJECT_ROOT pointing at the repo root (with pyproject.toml)
- Collect Git metadata (tag/branch/commit/time)
- Provide router SSH config and Windows PC target config
- Support SSH tunneling through Linux router to Windows target PC (plink port forward)
- NEW: Allow specifying device plugins (e.g., psa_horiba,dsv_horiba) and expose a unified pip-extras string
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
# Default PC/job profile; can be overridden by environment
if (-not $env:CI_JOB_NAME -or $env:CI_JOB_NAME -eq "") { $env:CI_JOB_NAME = "kinexus_blb" }

# Device plugins list (comma/semicolon/space separated). Override per run if needed.
# Examples: "psa_horiba,dsv_horiba" or "utm_zwick" or ""
$env:DEVICE_PLUGINS = if ($env:DEVICE_PLUGINS) { $env:DEVICE_PLUGINS } else { "rhe_kinexus" }

# Build unified pip-extras string (e.g., "ci,horiba_blb,psa_horiba,dsv_horiba")
$env:PIP_EXTRAS = Get-PipExtras -CiJob $env:CI_JOB_NAME -DevPlugins $env:DEVICE_PLUGINS

# Also expose as a script-scoped array for callers that dot-source this file
$script:DEVICE_PLUGIN_LIST = @()
if ($env:DEVICE_PLUGINS) { $script:DEVICE_PLUGIN_LIST = $env:DEVICE_PLUGINS -split '[,; ]+' | Where-Object { $_ } }

# ------------------------------
# Router Configuration (Linux Jump Host)
# ------------------------------
$env:ROUTER_IP   = if ($env:ROUTER_IP) { $env:ROUTER_IP } else { "134.169.58.199" }
$env:ROUTER_USER = if ($env:ROUTER_USER) { $env:ROUTER_USER } else { "ipat" }
$env:ROUTER_PORT = if ($env:ROUTER_PORT) { $env:ROUTER_PORT } else { 22 }

# ------------------------------
# Windows Target PC Configuration (Behind Router)
# ------------------------------
$env:TARGET_IP   = if ($env:TARGET_IP) { $env:TARGET_IP } else { "192.168.1.5" }
#{ "192.168.1.6" } -- haake_blb
$env:TARGET_USER = if ($env:TARGET_USER) { $env:TARGET_USER } else { "messrechner" }
#{ "extruder" } -- haake_blb
#{ "horiba" } -- horiba_blb
$env:TARGET_PORT = if ($env:TARGET_PORT) { $env:TARGET_PORT } else { 22 }

# Tunnel endpoint on local machine
$env:TARGET_TUNNEL_PORT = if ($env:TARGET_TUNNEL_PORT) { $env:TARGET_TUNNEL_PORT } else { 2222 }

# ------------------------------
# Certificates & Secure Passwords
# ------------------------------
$env:SIGNING_CERT_PFX = if ($env:SIGNING_CERT_PFX) { $env:SIGNING_CERT_PFX } else { "$env:USERPROFILE\.secure\ipat_wd.pfx" }

$pfxPassPath    = if ($env:PFX_PASS_PATH) { $env:PFX_PASS_PATH } else { Join-Path $env:USERPROFILE ".secure\pfxpass.txt" }
$routerPassPath = if ($env:ROUTER_PASS_PATH) { $env:ROUTER_PASS_PATH } else { "$env:USERPROFILE\.secure\misch_route.txt" }
$targetPassPath = if ($env:TARGET_PASS_PATH) { $env:TARGET_PASS_PATH } else { "$env:USERPROFILE\.secure\$env:CI_JOB_NAME.txt" }

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
# SSH private key files for authentication (PuTTY .ppk, same key you tested manually)
$env:ROUTER_SSH_KEY = if ($env:ROUTER_SSH_KEY) { $env:ROUTER_SSH_KEY } else { "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk" }
$env:TARGET_SSH_KEY = if ($env:TARGET_SSH_KEY) { $env:TARGET_SSH_KEY } else { "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk" }  # same .ppk as used in manual test

# Host keys in formats that plink accepts (prefer SHA256 fingerprints)
$env:ROUTER_SSH_HOSTKEY = if ($env:ROUTER_SSH_HOSTKEY) { $env:ROUTER_SSH_HOSTKEY } else { 'SHA256:uj6kBrFxe0qWj9SC3avJ5PTPCstPJ/Cp33v/VtiiWEk' }
$env:TARGET_SSH_HOSTKEY = if ($env:TARGET_SSH_HOSTKEY) { $env:TARGET_SSH_HOSTKEY } else { 'SHA256:i6nnK2fA8KvuY7EaepsdwnvghKFqDXlBd6e0g9zV6Tw' } # kinexus_blb
#{ 'SHA256:e1Aj6OvJNCXlNPv/asJo/jnuFKLkjEObTDi38g73Nt8' } --horiba_blb
#{ 'SHA256:NTbRZ+BQbSPmZp5tEtMq7E1p3muNU7kzGmviFX/COgk' } --haake_blb
#{ 'SHA256:i6nnK2fA8KvuY7EaepsdwnvghKFqDXlBd6e0g9zV6Tw' } --kinexus_blb

# (Alternative base64 form if you ever need it:)
# $env:ROUTER_SSH_HOSTKEY = 'ssh-ed25519:AAAAC3NzaC1lZDI1NTE5AAAAIFqvmR5Q0yi8vFlHQmPDmqSfapwMtuAKflpiUA9UpSUY'
# $env:TARGET_SSH_HOSTKEY = 'ssh-ed25519:AAAAC3NzaC1lZDI1NTE5AAAAIDnde8wPsHN7mxhOmEFyH2UFzAdpyBWCtgJ7hO/O1wWq'

# ------------------------------
# Paths
# ------------------------------
$env:REMOTE_PATH = if ($env:REMOTE_PATH) { $env:REMOTE_PATH } else { "C:\Watchdog" }
$env:REMOTE_EXE  = "$env:REMOTE_PATH\wd-$env:CI_JOB_NAME.exe"

# ------------------------------
# Tunnel Helpers
# ------------------------------
function Start-TargetTunnel {
    $plinkArgs = @(
        "-batch","-N",
        "-L","$($env:TARGET_TUNNEL_PORT):$($env:TARGET_IP):$($env:TARGET_PORT)",
        "-P",$env:ROUTER_PORT,
        "-i",$env:ROUTER_SSH_KEY,          # key for router hop
        "-hostkey",$env:ROUTER_SSH_HOSTKEY,# router host key (SHA256:... or ssh-ed25519:...)
        "$($env:ROUTER_USER)@$($env:ROUTER_IP)"
    )
    Write-Host "Starting SSH tunnel localhost:$($env:TARGET_TUNNEL_PORT) -> $($env:TARGET_IP):$($env:TARGET_PORT) via router..."
    $global:__TunnelProc = Start-Process -FilePath plink.exe -ArgumentList $plinkArgs -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 1
    if ($__TunnelProc.HasExited) {
        throw "Tunnel process exited early. Check router credentials/host key."
    }
    # Wait up to 8s for the local listener to appear
    $deadline = (Get-Date).AddSeconds(8)
    do {
        $listening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $env:TARGET_TUNNEL_PORT -State Listen -EA SilentlyContinue
        if ($listening) { break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if (-not $listening) { throw "Local tunnel port $($env:TARGET_TUNNEL_PORT) is not listening." }
}

function Invoke-TargetCommand {
    param([string]$Command)
    $plinkArgs = @(
        "-batch","-P",$env:TARGET_TUNNEL_PORT,
        "-i",$env:TARGET_SSH_KEY,          # key for target hop
        "-hostkey",$env:TARGET_SSH_HOSTKEY,# target host key (SHA256:... or ssh-ed25519:...)
        "$($env:TARGET_USER)@127.0.0.1",$Command
    )
    & plink.exe @plinkArgs
    return $LASTEXITCODE
}

function Copy-FileViaTunnel {
    param([string]$LocalFile, [string]$RemoteFile)
    $scpArgs = @(
        "-batch","-P",$env:TARGET_TUNNEL_PORT,
        "-i",$env:TARGET_SSH_KEY,
        "-hostkey",$env:TARGET_SSH_HOSTKEY,
        $LocalFile,"$($env:TARGET_USER)@127.0.0.1`:$RemoteFile"
    )
    & pscp.exe @scpArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed to copy $LocalFile" }
}

# ------------------------------
# Final Echo
# ------------------------------
Write-Host "Router-based env loaded:"
Write-Host "  CI_JOB_NAME        = '$($env:CI_JOB_NAME)'"
Write-Host "  DEVICE_PLUGINS     = '$($env:DEVICE_PLUGINS)'"
Write-Host "  PIP_EXTRAS         = '$($env:PIP_EXTRAS)'"
Write-Host "  ROUTER_IP          = '$($env:ROUTER_IP)'"
Write-Host "  TARGET_IP          = '$($env:TARGET_IP)'"
Write-Host "  TARGET_TUNNEL_PORT = '$($env:TARGET_TUNNEL_PORT)'"
Write-Host "  REMOTE_EXE         = '$($env:REMOTE_EXE)'"
Write-Host "Using TARGET_SSH_KEY = $env:TARGET_SSH_KEY (exists: $(Test-Path $env:TARGET_SSH_KEY))"
Write-Host "Using TARGET_SSH_HOSTKEY = $env:TARGET_SSH_HOSTKEY"
