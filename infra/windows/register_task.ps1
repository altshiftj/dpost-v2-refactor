<#
    register_task.ps1
    -----------------
    Creates or updates the IPAT-Watchdog Scheduled Task for correct deployment.

    • Starts the app from D:\WatchdogDeploy
    • Captures both stdout and stderr into logs\app_output.log
    • Restarts on crash (retry every 1 minute)
    • Works even if user is not admin
#>

# ─────────────────────────────────────────────
# Strict settings
# ─────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ─────────────────────────────────────────────
# Configurable variables
# ─────────────────────────────────────────────
$TaskName  = 'IPAT-Watchdog'
$ExePath   = 'D:\WatchdogDeploy\run.exe'
$LogDir    = 'D:\WatchdogDeploy\logs'
$LogPath   = Join-Path $LogDir 'app_output.log'
$UserName  = "$env:USERNAME"

# Restart policy
$RestartInterval = New-TimeSpan -Minutes 1
$RestartCount    = 9999

# ─────────────────────────────────────────────
# Prepare log folder
# ─────────────────────────────────────────────
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
if (Test-Path $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Move-Item $LogPath "$LogPath.$timestamp"
}

# ─────────────────────────────────────────────
# Unregister old task if it exists
# ─────────────────────────────────────────────
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# ─────────────────────────────────────────────
# Define the Scheduled Task parts
# ─────────────────────────────────────────────

# Launch powershell.exe → Push to D:\WatchdogDeploy → Run run.exe → Redirect stdout+stderr to log
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Push-Location 'D:\WatchdogDeploy'; & '$ExePath' *> '$LogPath'; Pop-Location`""

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
# Register the new Scheduled Task
# ─────────────────────────────────────────────
Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal

Write-Host "✅ Scheduled Task '$TaskName' (re)registered successfully."
