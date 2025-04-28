<#
    register_task.ps1
    -----------------
    Installs / updates the IPAT-Watchdog Scheduled Task.

    Requirements
    ------------
    • Windows 8 / Server 2012 or newer (Task Scheduler v2)
    • The user account that runs this script must be allowed to create Scheduled Tasks.
#>

# ─────────────────────────────────────────────
# 1 – strict settings so problems fail the CI
# ─────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ─────────────────────────────────────────────
# 2 – configurable variables
# ─────────────────────────────────────────────
$TaskName  = 'IPAT-Watchdog'
$ExePath   = 'D:\WatchdogDeploy\run.exe'
$LogDir    = 'D:\WatchdogDeploy\logs'
$LogPath   = Join-Path $LogDir 'app_output.log'
$UserName  = "$env:USERNAME"          # current interactive user

# Restart policy – must be at least PT1M
$RestartInterval = New-TimeSpan -Minutes 1   # 1 minute
$RestartCount    = 9999                      # practically forever

# ─────────────────────────────────────────────
# 3 – prepare log folder & rotate previous log
# ─────────────────────────────────────────────
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if (Test-Path $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Move-Item $LogPath "$LogPath.$timestamp"
}

# ─────────────────────────────────────────────
# 4 – remove any existing task (idempotent)
# ─────────────────────────────────────────────
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# ─────────────────────────────────────────────
# 5 – define the new task pieces
# ─────────────────────────────────────────────
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Start-Process -FilePath '$ExePath' -RedirectStandardOutput '$LogPath' -RedirectStandardError '$LogPath' -NoNewWindow`""

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartInterval $RestartInterval `
    -RestartCount    $RestartCount `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId   $UserName `
    -LogonType Interactive `
    -RunLevel Highest

# ─────────────────────────────────────────────
# 6 – register the task
# ─────────────────────────────────────────────
Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal

Write-Host "✅  Scheduled Task '$TaskName' (re)registered successfully."
