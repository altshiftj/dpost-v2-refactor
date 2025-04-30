<#
    register_task.ps1
    -----------------
    Creates or updates the IPAT-Watchdog Scheduled Task for correct deployment.

    • Starts the app from C:\Program Files\Watchdog
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
# Trust the code-signing certificate (if present)
# ─────────────────────────────────────────────
$CertPath = 'C:\Program Files\Watchdog\ipat_watchdog_signing.cer'

if (Test-Path $CertPath) {
    try {
        Write-Host "Installing code-signing certificate trust from: $CertPath"
        certutil -addstore -f "TrustedPublisher" $CertPath | Out-Null
        certutil -addstore -f "Root" $CertPath | Out-Null
        Write-Host "✅ Certificate installed to TrustedPublisher and Root stores."
    } catch {
        Write-Warning "⚠️ Failed to install certificate trust: $($_.Exception.Message)"
    }
} else {
    Write-Warning "⚠️ No certificate found at $CertPath — skipping trust installation."
}

# ─────────────────────────────────────────────
# Configurable variables
# ─────────────────────────────────────────────
$TaskName  = 'IPAT-Watchdog'
$ExePath   = 'C:\Program Files\Watchdog\run.exe'
$LogDir    = 'C:\Program Files\Watchdog\logs'
$LogPath   = Join-Path $LogDir 'watchdog.log'
$UserName  = "$env:USERNAME"

# ─────────────────────────────────────────────
# Stop any existing Watchdog task and running app
# ─────────────────────────────────────────────

# Stop the scheduled task if running
try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "No running scheduled task to stop."
}

# Kill lingering run.exe processes (safety net)
Get-Process run -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Killing leftover process PID=$($_.Id)"
    $_ | Stop-Process -Force
    Start-Sleep -Seconds 1
}

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

# Launch powershell.exe → Push to C:\Program Files\Watchdog → Run run.exe → Redirect stdout+stderr to log
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command \"Push-Location 'C:\Program Files\Watchdog'; & '$ExePath' *> '$LogPath'; Pop-Location\""

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
