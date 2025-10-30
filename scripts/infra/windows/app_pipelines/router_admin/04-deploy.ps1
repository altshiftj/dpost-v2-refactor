# 04-deploy.ps1 — No override .env

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

$remotePath = $env:REMOTE_PATH
$ciJobName  = $env:CI_JOB_NAME
$routerIP   = $env:ROUTER_IP
$routerUser = $env:ROUTER_USER
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER

$tunnelPort = $env:TARGET_TUNNEL_PORT
if (-not $tunnelPort) { $tunnelPort = 2222 }

$binaryName            = "wd-${ciJobName}.exe"
$distBinaryPath        = "dist\$binaryName"
$exePath               = Join-Path $remotePath $binaryName
# Read the job-aware build version metadata
$buildVersionPath      = "build\version-$ciJobName.txt"
# NEW: attach job name to version filename for clarity per-target
$deployVersionFilename = "version-$ciJobName.txt"
$deployVersionPath     = $deployVersionFilename

if (!(Test-Path $distBinaryPath))     { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path $buildVersionPath))   { Write-Error "$buildVersionPath missing. Did you run the build?"; exit 1 }

# Produce job-scoped deploy version file (augment build/version-<job>.txt with deploy info)
$deployMeta = @"
DEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z
CI_JOB_NAME=$env:CI_JOB_NAME
DEVICE_PLUGINS=$env:DEVICE_PLUGINS
PIP_EXTRAS=$env:PIP_EXTRAS
"@
(Get-Content $buildVersionPath) + $deployMeta | Set-Content -Encoding UTF8 $deployVersionPath

$start = Get-Date

# Tool check
if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
  Write-Error 'plink / pscp not in PATH.'; exit 1
}

Write-Host "Using ROUTER_SSH_KEY     = $env:ROUTER_SSH_KEY (exists: $(Test-Path $env:ROUTER_SSH_KEY))"
Write-Host "Using ROUTER_SSH_HOSTKEY = $env:ROUTER_SSH_HOSTKEY"
Write-Host "Using TARGET_SSH_KEY     = $env:TARGET_SSH_KEY (exists: $(Test-Path $env:TARGET_SSH_KEY))"
Write-Host "Using TARGET_SSH_HOSTKEY = $env:TARGET_SSH_HOSTKEY"

function Test-RouterConnection {
  Write-Host "Testing router connection ($env:ROUTER_USER@$env:ROUTER_IP)..."
  $args = @("-batch","-P",$env:ROUTER_PORT,"-i",$env:ROUTER_SSH_KEY,"-hostkey",$env:ROUTER_SSH_HOSTKEY,"$env:ROUTER_USER@$env:ROUTER_IP","echo hello-router")
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

  $deadline = (Get-Date).AddSeconds(8)
  do {
    $listening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $tunnelPort -State Listen -EA SilentlyContinue
    if ($listening) { break }
    Start-Sleep -Milliseconds 250
  } while ((Get-Date) -lt $deadline)
  if (-not $listening) { throw "Local tunnel port $tunnelPort is not listening." }
  Write-Host ("Tunnel process started (PID " + $__TunnelProc.Id + ").")
}

function Invoke-TargetCommand { param([string]$Command)
  $args = @("-batch","-P",$tunnelPort,"-i",$env:TARGET_SSH_KEY,"-hostkey",$env:TARGET_SSH_HOSTKEY,"$targetUser@127.0.0.1",$Command)
  Write-Host "plink : $($args -join ' ')"
  $out = & plink.exe @args 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "plink failed (exit $LASTEXITCODE). Output:"; $out | ForEach-Object { Write-Host "  $_" }
    Write-Warning "Re-running with -v..."; (& plink.exe @("-v") + $args 2>&1) | ForEach-Object { Write-Host "  $_" }
    $ok = $false; try { $tnc = Test-NetConnection -ComputerName 127.0.0.1 -Port $tunnelPort -WarningAction SilentlyContinue; $ok = $tnc -and $tnc.TcpTestSucceeded } catch {}
    Write-Host "Tunnel port $tunnelPort listening: $ok"
    return 1
  }
  return 0
}

function Copy-FileViaTunnel { param([string]$LocalFile, [string]$RemoteFile)
  $args = @("-batch","-P",$tunnelPort,"-i",$env:TARGET_SSH_KEY,"-hostkey",$env:TARGET_SSH_HOSTKEY,$LocalFile,"$targetUser@127.0.0.1`:$RemoteFile")
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

Write-Host "`n=== Step 0: Checking connections ==="
try {
  Test-RouterConnection
  Start-TargetTunnel
  Write-Host ("Testing target PC connectivity (" + $targetUser + "@" + $targetIP + " via tunnel)...")
  if (Invoke-TargetCommand "echo hello-target") { throw "Target PC not reachable through tunnel." }
  Write-Host "Target PC connection OK."
} catch {
  Write-Error ("Connectivity check failed: " + $_); Stop-TargetTunnel; exit 1
}

Write-Host "`n=== Step 1: Preparing target Windows PC ==="
$prepScript = @"
`$p      = '$remotePath'
`$exe    = '$binaryName'
`$path   = Join-Path `$p `$exe
`$verNew = 'version-$ciJobName.txt'
`$verOld = 'version.txt'

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

Get-ScheduledTask | Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
  ForEach-Object {
    Stop-ScheduledTask       -TaskName `$_.TaskName -EA SilentlyContinue
    Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false
  }
Start-Sleep 2

Get-Process -EA SilentlyContinue | Where-Object { `$_.Path -eq `$path } | Stop-Process -Force

# Rotate only the files we actually deploy
# 1) Always rotate the exe if present (to wd-*_backup.exe)
foreach (`$f in @(`$exe)) {
  `$src = Join-Path `$p `$f
  if (Test-Path `$src) {
    `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
    if (Test-Path `$bak) { Remove-Item `$bak -Force }
    Rename-Item -Path `$src -NewName `$bak -Force
  }
}

# 2) Version file rotation with job-aware naming
`$verNewPath = Join-Path `$p `$verNew
`$verOldPath = Join-Path `$p `$verOld
if (Test-Path `$verNewPath) {
  # Standard path exists -> rotate to version-<job>_backup.txt
  `$bak = `$verNewPath -replace '\.(\w+)$','_backup.`$1'
  if (Test-Path `$bak) { Remove-Item `$bak -Force }
  Rename-Item -Path `$verNewPath -NewName `$bak -Force
} elseif (Test-Path `$verOldPath) {
  # Legacy file exists -> migrate backup name into job-aware backup
  `$bak = Join-Path `$p ("version-$ciJobName`_backup.txt")
  if (Test-Path `$bak) { Remove-Item `$bak -Force }
  Rename-Item -Path `$verOldPath -NewName `$bak -Force
}
Write-Host "Windows PC preparation complete"
"@

$encodedPrep = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prepScript))
if (Invoke-TargetCommand "powershell -NoProfile -EncodedCommand $encodedPrep") {
  Write-Error "Target PC preparation failed."; Stop-TargetTunnel; exit 1
}

Write-Host "`n=== Step 2: Transferring files ==="
$items = @(
  @{ Local = $distBinaryPath;     Label = $binaryName;               Remote = $binaryName },
  @{ Local = $deployVersionPath;  Label = $deployVersionFilename;     Remote = $deployVersionFilename }
)
foreach ($it in $items) {
  $localPath      = $it.Local
  $remoteFilePath = Join-Path $env:REMOTE_PATH $it.Remote
  if (!(Test-Path -LiteralPath $localPath)) { Write-Error "Local file missing: $localPath"; Stop-TargetTunnel; exit 1 }
  Write-Host "Transferring $($it.Label)..."
  try { Copy-FileViaTunnel -LocalFile $localPath -RemoteFile $remoteFilePath; Write-Host "    OK" }
  catch { Write-Error ("FAILED to transfer " + $it.Label + ": " + $_); Stop-TargetTunnel; exit 1 }
}

Write-Host "`n=== Step 3: Verifying deployment ==="
$verifyScript = @"
`$remotePath = '$env:REMOTE_PATH'
`$binaryName = '$binaryName'
`$exePath = Join-Path `$remotePath `$binaryName

Write-Host "Checking deployed files..."
if (Test-Path `$exePath) {
  `$size = (Get-Item `$exePath).Length
  `$sizeMB = [math]::Round(`$size / 1MB, 2)
  Write-Host "OK: Executable deployed: `$exePath (`$sizeMB MB)"
} else { Write-Error "MISSING: Executable not found: `$exePath"; exit 1 }

`$verFile = Join-Path `$remotePath '$deployVersionFilename'
if (Test-Path `$verFile) {
  Write-Host "OK: Version file deployed: `$verFile"
  Get-Content `$verFile | ForEach-Object { Write-Host "  `$_" }
} else { Write-Warning "MISSING: Version file not found: `$verFile" }

Write-Host "Deployment verification complete"
"@
$encodedVerify = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($verifyScript))
if (Invoke-TargetCommand "powershell -NoProfile -EncodedCommand $encodedVerify") {
  Write-Warning "Deployment verification had issues, but continuing..."
}

$elapsed = (Get-Date) - $start
Write-Host "`n=== Deployment Complete ==="
Write-Host "Total time: $($elapsed.ToString('hh\:mm\:ss'))"
Write-Host "Deployed to: $targetIP via router $routerIP (tunnel on localhost:$tunnelPort)"

Stop-TargetTunnel
