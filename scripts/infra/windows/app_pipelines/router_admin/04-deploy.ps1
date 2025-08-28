# 04-deploy.ps1  (Tunnel model with Step 0 checks + rich diagnostics)

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

$remotePath = $env:REMOTE_PATH
$ciJobName  = $env:CI_JOB_NAME
$routerIP   = $env:ROUTER_IP
$routerUser = $env:ROUTER_USER
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER

# Default tunnel port if not provided
$tunnelPort = $env:TARGET_TUNNEL_PORT
if (-not $tunnelPort) { $tunnelPort = 2222 }

$binaryName     = "wd-${ciJobName}.exe"
$distBinaryPath = "dist\$binaryName"
$exePath        = Join-Path $remotePath $binaryName
$filesToDeploy  = @($binaryName, 'version.txt', 'scripts\infra\windows\utils\register_task.ps1')

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

Write-Host "Using ROUTER_SSH_KEY     = $env:ROUTER_SSH_KEY (exists: $(Test-Path $env:ROUTER_SSH_KEY))"
Write-Host "Using ROUTER_SSH_HOSTKEY = $env:ROUTER_SSH_HOSTKEY"
Write-Host "Using TARGET_SSH_KEY     = $env:TARGET_SSH_KEY (exists: $(Test-Path $env:TARGET_SSH_KEY))"
Write-Host "Using TARGET_SSH_HOSTKEY = $env:TARGET_SSH_HOSTKEY"

# ------------------------------
# Helpers
# ------------------------------
function Test-RouterConnection {
    Write-Host "Testing router connection ($env:ROUTER_USER@$env:ROUTER_IP)..."
    $args = @(
        "-batch","-P",$env:ROUTER_PORT,
        "-i",$env:ROUTER_SSH_KEY,
        "-hostkey",$env:ROUTER_SSH_HOSTKEY,
        "$env:ROUTER_USER@$env:ROUTER_IP","echo hello-router"
    )
    & plink.exe @args
    if ($LASTEXITCODE -ne 0) { throw "Router connection failed." }
    Write-Host "Router connection OK."
}

function Start-TargetTunnel {
    $args = @(
        "-batch","-N",
        "-L","$($tunnelPort):$($targetIP):$($env:TARGET_PORT)",
        "-P",$env:ROUTER_PORT,
        "-i",$env:ROUTER_SSH_KEY,
        "-hostkey",$env:ROUTER_SSH_HOSTKEY,
        "$env:ROUTER_USER@$env:ROUTER_IP"
    )
    Write-Host "Starting SSH tunnel localhost:$tunnelPort -> ${targetIP}:$($env:TARGET_PORT) via router..."
    $global:__TunnelProc = Start-Process -FilePath plink.exe -ArgumentList $args -PassThru -WindowStyle Hidden
    Start-Sleep 1
    if ($__TunnelProc.HasExited) { throw "Tunnel process exited early. Check router credentials/host key." }

    # Wait up to 8s for local port to listen
    $deadline = (Get-Date).AddSeconds(8)
    do {
        $listening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $tunnelPort -State Listen -EA SilentlyContinue
        if ($listening) { break }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    if (-not $listening) { throw "Local tunnel port $tunnelPort is not listening." }

    Write-Host ("Tunnel process started (PID " + $__TunnelProc.Id + ").")
}

function Invoke-TargetCommand {
    param([string]$Command)

    $args = @(
        "-batch","-P",$tunnelPort,
        "-i",$env:TARGET_SSH_KEY,
        "-hostkey",$env:TARGET_SSH_HOSTKEY,
        "$targetUser@127.0.0.1",$Command
    )

    Write-Host "plink : $($args -join ' ')"
    $out = & plink.exe @args 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Warning "plink to target failed (exit $code). Output:"
        $out | ForEach-Object { Write-Host "  $_" }

        # One more try with -v added for richer diagnostics
        Write-Warning "Re-running once with -v for diagnostics..."
        $vargs = @("-v") + $args
        $vout = & plink.exe @vargs 2>&1
        $vcode = $LASTEXITCODE
        $vout | ForEach-Object { Write-Host "  $_" }

        # Port sanity check
        $portOk = $false
        try {
            $tnc = Test-NetConnection -ComputerName 127.0.0.1 -Port $tunnelPort -WarningAction SilentlyContinue
            if ($tnc -and $tnc.TcpTestSucceeded) { $portOk = $true }
        } catch {}
        Write-Host "Tunnel port $tunnelPort listening: $portOk"

        return 1
    }
    return 0
}

function Copy-FileViaTunnel {
    param([string]$LocalFile, [string]$RemoteFile)
    $args = @(
        "-batch","-P",$tunnelPort,
        "-i",$env:TARGET_SSH_KEY,
        "-hostkey",$env:TARGET_SSH_HOSTKEY,
        $LocalFile,"$targetUser@127.0.0.1`:$RemoteFile"
    )
    Write-Host "pscp : $($args -join ' ')"
    & pscp.exe @args
    if ($LASTEXITCODE -ne 0) { throw "Failed to copy $LocalFile" }
}

function Stop-TargetTunnel {
    if ($null -ne $global:__TunnelProc -and -not $global:__TunnelProc.HasExited) {
        Write-Host ("Stopping tunnel process (PID " + $global:__TunnelProc.Id + ")...")
        try { $global:__TunnelProc.CloseMainWindow() | Out-Null } catch {}
        Start-Sleep 0.5
        try { if (-not $global:__TunnelProc.HasExited) { $global:__TunnelProc.Kill() | Out-Null } } catch {}
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

# Explicit mapping: Local file path → Remote filename under C:\Watchdog
$items = @(
    @{ Local = $distBinaryPath;                                   Label = $binaryName;     Remote = $binaryName },
    @{ Local = 'version.txt';                                     Label = 'version.txt';   Remote = 'version.txt' },
    @{ Local = 'scripts\infra\windows\utils\register_task.ps1';   Label = 'register_task.ps1'; Remote = 'register_task.ps1' }
)

foreach ($it in $items) {
    $localPath      = $it.Local
    $remoteFilePath = Join-Path $env:REMOTE_PATH $it.Remote

    if (!(Test-Path -LiteralPath $localPath)) {
        Write-Error "Local file missing: $localPath"
        Stop-TargetTunnel
        exit 1
    }

    Write-Host "Transferring $($it.Label)..."
    try {
        Copy-FileViaTunnel -LocalFile $localPath -RemoteFile $remoteFilePath
        Write-Host "    OK: $($it.Label) transferred successfully"
    } catch {
        Write-Error ("FAILED to transfer " + $it.Label + ": " + $_)
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
