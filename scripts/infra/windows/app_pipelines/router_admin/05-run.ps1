<#
    Register and start Windows service/task via router SSH hop
    - SSH to router, then SSH from router to Windows PC
    - Execute task registration remotely
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# --- SETTINGS ---------------------------------------------------------
$ciJobName   = $env:CI_JOB_NAME
$routerIP    = $env:ROUTER_IP
$targetIP    = $env:TARGET_IP

$taskName = "IPAT-Watchdog-$ciJobName"
$exePath  = "$env:REMOTE_PATH\wd-$ciJobName.exe"

# ── TOOL CHECK ────────────────────────────────────────────────────────
if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH. Add PuTTY to your environment variables."
    exit 1
}

# ── TIMER START ───────────────────────────────────────────────────────
$startTime = Get-Date
Write-Host "Registering task '$taskName' on $targetIP via router $routerIP..."

# ── BUILD WINDOWS TASK REGISTRATION COMMAND ──────────────────────────
$windowsTaskCmd = @(
    'powershell',
    '-NoProfile',
    '-ExecutionPolicy Bypass',
    '-File', "$env:REMOTE_PATH\register_task.ps1",
    '-TaskName', "`"$taskName`"",
    '-ExePath',  "`"$exePath`""
) -join ' '

# ── EXECUTE VIA DOUBLE SSH HOP ────────────────────────────────────────
Write-Host "Executing task registration via double SSH hop..."

$doubleSSHCommand = Get-DoubleSSHCommand -WindowsCommand $windowsTaskCmd
$routerArgs = Get-RouterSSHCommand -Command $doubleSSHCommand

& plink.exe @routerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote task registration failed (exit code $LASTEXITCODE)"
    exit 1
}

# ── VERIFY TASK REGISTRATION ──────────────────────────────────────────
Write-Host "`nVerifying task registration..."

$verifyScript = @"
try {
    `$task = Get-ScheduledTask -TaskName '$taskName' -ErrorAction Stop
    Write-Host "✓ Task '$taskName' registered successfully"
    Write-Host "  State: `$(`$task.State)"
    Write-Host "  Author: `$(`$task.Author)"
    Write-Host "  Description: `$(`$task.Description)"
    
    # Try to start the task
    Start-ScheduledTask -TaskName '$taskName'
    Start-Sleep -Seconds 3
    
    `$taskInfo = Get-ScheduledTaskInfo -TaskName '$taskName'
    Write-Host "  Last Result: `$(`$taskInfo.LastTaskResult)"
    Write-Host "  Last Run Time: `$(`$taskInfo.LastRunTime)"
    Write-Host "  Next Run Time: `$(`$taskInfo.NextRunTime)"
    
} catch {
    Write-Error "✗ Task verification failed: `$(`$_.Exception.Message)"
    exit 1
}
"@

$encodedVerify = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($verifyScript))
$verifyCommand = "powershell -NoProfile -EncodedCommand $encodedVerify"
$doubleSSHVerify = Get-DoubleSSHCommand -WindowsCommand $verifyCommand

$verifyArgs = Get-RouterSSHCommand -Command $doubleSSHVerify
& plink.exe @verifyArgs

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Task verification had issues, but task may still be registered"
}

# ── TIMER END ─────────────────────────────────────────────────────────
$duration = (Get-Date) - $startTime
Write-Host "`n=== Task Registration Complete ==="
Write-Host "Task: $taskName"
Write-Host "Target: $targetIP (via router $routerIP)"
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
