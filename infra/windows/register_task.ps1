<#
    register_task.ps1
    -----------------
    Creates or updates the IPAT-Watchdog Scheduled Task for correct deployment.

    • Starts the app from C:\Watchdog
    • Captures both stdout and stderr into logs\watchdog.log
    • Restarts on crash (retry every 1 minute)
    • Requires Administrator privileges (checked at runtime)
#>

# ─────────────────────────────────────────────
# Strict settings and admin check
# ─────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Warning "This script must be run as Administrator. Exiting."
    exit 1
}

# ─────────────────────────────────────────────
# Configurable variables
# ─────────────────────────────────────────────
$TaskName  = 'IPAT-Watchdog'
$ExePath   = 'C:\Watchdog\run.exe'
$LogDir    = 'C:\Watchdog\logs'
$LogPath   = Join-Path $LogDir 'watchdog.log'
$UserName  = "$env:USERNAME"

# ─────────────────────────────────────────────
# Stop any existing Watchdog task and running app
# ─────────────────────────────────────────────
try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "No running scheduled task to stop."
}

Get-Process run -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Killing leftover process PID=$($_.Id)"
    $_ | Stop-Process -Force
    Start-Sleep -Seconds 1
}

# ─────────────────────────────────────────────
# Restart policy
# ─────────────────────────────────────────────
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
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Push-Location 'C:\Watchdog'; & '$ExePath' *> '$LogPath'; Pop-Location`""

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

Write-Host "Scheduled Task '$TaskName' (re)registered successfully."
