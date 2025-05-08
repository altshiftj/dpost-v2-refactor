# Declare script parameters
param (
    [string]$TaskName,   # Optional custom name for the scheduled task
    [string]$ExePath,    # Optional path to the executable to run
    [string]$LogDir      # Optional directory where logs will be stored
)

# Stop on any error and enforce strict variable use
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ─────────────────────────────────────────────────────
# Ensure script is running with administrative privileges
# ─────────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Run this script as Administrator."
    exit 1
}

# ─────────────────────────────────────────────────────
# Locate the most recent Watchdog executable if not provided
# ─────────────────────────────────────────────────────
$defaultDir = "C:\Watchdog"

if (-not $ExePath) {
    # Select the newest wd-*.exe file
    $ExePath = Get-ChildItem "$defaultDir\wd-*.exe" -File |
               Sort-Object LastWriteTime -Descending |
               Select-Object -First 1 |
               ForEach-Object { $_.FullName }

    if (-not $ExePath) {
        throw "No wd-*.exe found in $defaultDir."
    }
}

# Extract executable directory and filename (without extension)
$ExeDir  = Split-Path $ExePath -Parent
$ExeName = [IO.Path]::GetFileNameWithoutExtension($ExePath)

# Default task name if none provided
if (-not $TaskName) {
    $TaskName = "IPAT-Watchdog-$ExeName"
}

# ─────────────────────────────────────────────────────
# Set up log file path
# ─────────────────────────────────────────────────────
if (-not $LogDir) {
    $LogDir = Join-Path $ExeDir 'logs'
}
$LogPath = Join-Path $LogDir "$TaskName.log"

# ─────────────────────────────────────────────────────
# Remove any existing scheduled task and kill process
# ─────────────────────────────────────────────────────
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask       -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Start-Sleep 2
}

# Kill any currently running process matching the EXE path
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $ExePath } |
    Stop-Process -Force

# ─────────────────────────────────────────────────────
# Prepare log directory and archive old log if needed
# ─────────────────────────────────────────────────────
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

if (Test-Path $LogPath) {
    $ts         = Get-Date -Format 'yyyyMMdd-HHmmss'
    $base       = [IO.Path]::GetFileNameWithoutExtension($LogPath)
    $ext        = [IO.Path]::GetExtension($LogPath)        # e.g., ".log"
    $backupName = "$base-$ts$ext"                          # e.g., watchdog‑20250506‑164903.log
    Rename-Item -Path $LogPath -NewName $backupName -Force
}

# ─────────────────────────────────────────────────────
# Define the scheduled task components
# ─────────────────────────────────────────────────────

# Task action: run powershell, redirect output to log file
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"& { Push-Location '$ExeDir'; & '$ExePath' *> '$LogPath'; Pop-Location }`""

# Trigger task at user logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Task settings: auto-restart on failure, prevent concurrent runs
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 9999 `
    -MultipleInstances IgnoreNew

# Run the task with the current user, elevated
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Register and start the task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
Start-ScheduledTask -TaskName $TaskName

# ─────────────────────────────────────────────────────
# Display output for user reference
# ─────────────────────────────────────────────────────
Write-Host "`nRegistered task: $TaskName"
Write-Host "EXE : $ExePath"
Write-Host "Log : $LogPath"
