<#
    Register and start Windows scheduled task via router SSH hop
    Uses tunnel helpers from 00-env.ps1
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# --- SETTINGS ---------------------------------------------------------
$ciJobName = $env:CI_JOB_NAME
$routerIP  = $env:ROUTER_IP
$targetIP  = $env:TARGET_IP

$taskName = "IPAT-Watchdog-$ciJobName"
$exePath  = "$env:REMOTE_PATH\wd-$ciJobName.exe"

# ── TOOL CHECK ────────────────────────────────────────────────────────
if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH."
    exit 1
}

# ── TIMER START ───────────────────────────────────────────────────────
$startTime = Get-Date
Write-Host "Registering task '$taskName' on $targetIP via router $routerIP..."
Write-Host "Executing task registration via SSH tunnel..."

# ── OPEN TUNNEL ───────────────────────────────────────────────────────
Start-TargetTunnel

# ── BUILD WINDOWS TASK REGISTRATION COMMAND ───────────────────────────
$windowsTaskCmd = @(
    'powershell','-NoProfile','-ExecutionPolicy Bypass',
    '-File', "$env:REMOTE_PATH\register_task.ps1",
    '-TaskName', "`"$taskName`"",
    '-ExePath',  "`"$exePath`"",
    '-WorkingDir', "`"$env:REMOTE_PATH`""
) -join ' '

# ── EXECUTE ON TARGET VIA TUNNEL ─────────────────────────────────────
Invoke-TargetCommand -Command $windowsTaskCmd
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    Write-Error "Remote task registration failed (exit code $rc)"
    Stop-TargetTunnel
    exit 1
}

# ── VERIFY TASK REGISTRATION ──────────────────────────────────────────
$verifyScript = @"
try {
    `$task = Get-ScheduledTask -TaskName '$taskName' -ErrorAction Stop
    Write-Host "✓ Task '$taskName' registered successfully"
    Start-ScheduledTask -TaskName '$taskName'
    Start-Sleep -Seconds 3
    `$info = Get-ScheduledTaskInfo -TaskName '$taskName'
    Write-Host "  Last Result: `$(`$info.LastTaskResult)"
    Write-Host "  Last Run Time: `$(`$info.LastRunTime)"
    Write-Host "  Next Run Time: `$(`$info.NextRunTime)"
} catch {
    Write-Error "Task verification failed: `$($_.Exception.Message)"
    exit 1
}
"@

$encodedVerify = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($verifyScript))
$verifyCommand = "powershell -NoProfile -EncodedCommand $encodedVerify"

Invoke-TargetCommand -Command $verifyCommand
$vrc = $LASTEXITCODE
if ($vrc -ne 0) {
    Write-Warning "Task verification had issues (exit $vrc)."
}

# ── TIMER END ─────────────────────────────────────────────────────────
$duration = (Get-Date) - $startTime
Write-Host "`n=== Task Registration Complete ==="
Write-Host "Task: $taskName"
Write-Host "Target: $targetIP (via router $routerIP)"
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)

# Close tunnel
if ($global:__TunnelProc -and -not $global:__TunnelProc.HasExited) {
    try { $global:__TunnelProc.Kill() | Out-Null } catch {}
}
