# 04-deploy.ps1  (Tunnel model with Step 0 checks)

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

$remotePath = $env:REMOTE_PATH
$ciJobName  = $env:CI_JOB_NAME
$routerIP   = $env:ROUTER_IP
$routerUser = $env:ROUTER_USER
$routerPass = $env:ROUTER_PASS
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
# $targetPass = $env:TARGET_PASS  # No longer needed - using SSH keys

# Default tunnel port if not provided
$tunnelPort = $env:TARGET_TUNNEL_PORT
if (-not $tunnelPort) { $tunnelPort = 2222 }

$binaryName     = "wd-${ciJobName}.exe"
$distBinaryPath = "dist\$binaryName"
$exePath        = Join-Path $remotePath $binaryName
$filesToDeploy  = @($binaryName, 'version.txt', 'scripts/infra/windows/register_task.ps1')

if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path 'version.txt'))   { Write-Error "version.txt missing.";     exit 1 }

# Update version.txt with deployment timestamp
@"
COMMIT_TAG=$env:COMMIT_TAG
COMMIT_HASH=$env:COMMIT_HASH
GIT_BRANCH=$env:GIT_BRANCH
BUILD_TIME=$env:BUILD_TIME
DEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z
"@ | Set-Content -Encoding UTF8 version.txt

$start = Get-Date

# Tool check
if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
    Write-Error 'plink / pscp not in PATH.'; exit 1
}

# ------------------------------
# Helpers
# ------------------------------
function Test-RouterConnection {
    Write-Host "Testing router connection ($env:ROUTER_USER@$env:ROUTER_IP)..."
    $plinkArgs = @(
        "-batch", "-P", $env:ROUTER_PORT,
        "-i", $env:ROUTER_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:ROUTER_SSH_HOSTKEY,
        "$env:ROUTER_USER@$env:ROUTER_IP", "echo hello-router"
    )
    & plink.exe @plinkArgs
    if ($LASTEXITCODE -ne 0) { throw "Router connection failed." }
    Write-Host "Router connection OK."
}

function Start-TargetTunnel {
    $plinkArgs = @(
        "-batch", "-N",
        "-L", "$($tunnelPort):$($targetIP):$($env:TARGET_PORT)",
        "-P", $env:ROUTER_PORT,
        "-i", $env:ROUTER_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:ROUTER_SSH_HOSTKEY,
        "$env:ROUTER_USER@$env:ROUTER_IP"
    )
    Write-Host "Starting SSH tunnel localhost:$tunnelPort -> $targetIP:22 via router..."
    $global:__TunnelProc = Start-Process -FilePath plink.exe -ArgumentList $plinkArgs -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    if ($__TunnelProc.HasExited) {
        throw "Tunnel process exited early. Check router credentials or router host key."
    }
    Write-Host ("Tunnel process started (PID " + $__TunnelProc.Id + ").")
}

function Invoke-TargetCommand {
    param([string]$Command)
    $plinkArgs = @(
        "-batch", "-P", $tunnelPort,
        "-i", $env:TARGET_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:TARGET_SSH_HOSTKEY,
        "$targetUser@127.0.0.1", $Command
    )
    & plink.exe @plinkArgs
    return $LASTEXITCODE
}

function Copy-FileViaTunnel {
    param([string]$LocalFile, [string]$RemoteFile)
    $scpArgs = @(
        "-batch", "-P", $tunnelPort,
        "-i", $env:TARGET_SSH_KEY,  # Use SSH key instead of password
        "-hostkey", $env:TARGET_SSH_HOSTKEY,
        $LocalFile, "$targetUser@127.0.0.1`:$RemoteFile"
    )
    & pscp.exe @scpArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed to copy $LocalFile" }
}

function Stop-TargetTunnel {
    if ($null -ne $global:__TunnelProc -and -not $global:__TunnelProc.HasExited) {
        Write-Host ("Stopping tunnel process (PID " + $global:__TunnelProc.Id + ")...")
        try { $global:__TunnelProc.CloseMainWindow() | Out-Null } catch {}
        try { $global:__TunnelProc.Kill() | Out-Null } catch {}
    }
}

# ------------------------------
# Step 0: Connectivity checks
# ------------------------------
Write-Host ""
Write-Host "=== Step 0: Checking connections ==="
try {
    Test-RouterConnection

    Start-TargetTunnel

    Write-Host ("Testing target PC connectivity (" + $targetUser + "@" + $targetIP + " via tunnel)...")
    if (Invoke-TargetCommand "echo hello-target") {
        throw "Target PC not reachable through tunnel."
    }
    Write-Host "Target PC connection OK."
} catch {
    Write-Error ("Connectivity check failed: " + $_)
    Stop-TargetTunnel
    exit 1
}

# ------------------------------
# Step 1: Prepare Windows PC
# ------------------------------
Write-Host ""
Write-Host "=== Step 1: Preparing target Windows PC ==="

$prepScript = @"
`$p      = '$remotePath'
`$exe    = '$binaryName'
`$path   = Join-Path `$p `$exe

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

Get-ScheduledTask | Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
    ForEach-Object {
        Stop-ScheduledTask       -TaskName `$_.TaskName -EA SilentlyContinue
        Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false
    }
Start-Sleep 2

Get-Process -EA SilentlyContinue |
    Where-Object { `$_.Path -eq `$path } |
    Stop-Process -Force

foreach (`$f in @(`$exe,'version.txt')) {
    `$src = Join-Path `$p `$f
    if (Test-Path `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        if (Test-Path `$bak) { Remove-Item `$bak -Force }
        Rename-Item -Path `$src -NewName `$bak -Force
    }
}
Write-Host "Windows PC preparation complete"
"@

$encodedPrep = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prepScript))
$windowsCommand = "powershell -NoProfile -EncodedCommand $encodedPrep"
if (Invoke-TargetCommand $windowsCommand) {
    Write-Error "Target PC preparation failed."
    Stop-TargetTunnel
    exit 1
}

# ------------------------------
# Step 2: Transfer files
# ------------------------------
Write-Host ""
Write-Host "=== Step 2: Transferring files ==="

foreach ($file in $filesToDeploy) {
    Write-Host "Transferring $file..."
    $localPath = switch ($file) {
        $binaryName { $distBinaryPath }
        'version.txt' { 'version.txt' }
        'scripts/infra/windows/register_task.ps1' { 'scripts/infra/windows/register_task.ps1' }
    }
    $remoteFilePath = Join-Path $env:REMOTE_PATH $file

    try {
        Copy-FileViaTunnel -LocalFile $localPath -RemoteFile $remoteFilePath
        Write-Host "    OK: $file transferred successfully"
    } catch {
        Write-Error ("FAILED to transfer " + $file + ": " + $_)
        Stop-TargetTunnel
        exit 1
    }
}

# ------------------------------
# Step 3: Verify deployment
# ------------------------------
Write-Host ""
Write-Host "=== Step 3: Verifying deployment ==="

$verifyScript = @"
`$remotePath = '$env:REMOTE_PATH'
`$binaryName = '$binaryName'
`$exePath = Join-Path `$remotePath `$binaryName

Write-Host "Checking deployed files..."
if (Test-Path `$exePath) {
    `$size = (Get-Item `$exePath).Length
    `$sizeMB = [math]::Round(`$size / 1MB, 2)
    Write-Host "OK: Executable deployed: `$exePath (`$sizeMB MB)"
} else {
    Write-Error "MISSING: Executable not found: `$exePath"
    exit 1
}

if (Test-Path (Join-Path `$remotePath 'version.txt')) {
    Write-Host "OK: Version file deployed"
    Get-Content (Join-Path `$remotePath 'version.txt') | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Warning "MISSING: Version file not found"
}

if (Test-Path (Join-Path `$remotePath 'register_task.ps1')) {
    Write-Host "OK: Task registration script deployed"
} else {
    Write-Warning "MISSING: Task registration script not found"
}

Write-Host "Deployment verification complete"
"@

$encodedVerify = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($verifyScript))
$verifyCommand = "powershell -NoProfile -EncodedCommand $encodedVerify"
if (Invoke-TargetCommand $verifyCommand) {
    Write-Warning "Deployment verification had issues, but continuing..."
}

# ------------------------------
# Finish
# ------------------------------
$elapsed = (Get-Date) - $start
Write-Host ""
Write-Host "=== Deployment Complete ==="
Write-Host "Total time: $($elapsed.ToString('hh\:mm\:ss'))"
Write-Host "Deployed to: $targetIP via router $routerIP (tunnel on localhost:$tunnelPort)"

# Optional: stop the tunnel; comment out if you prefer to keep it open
Stop-TargetTunnel
