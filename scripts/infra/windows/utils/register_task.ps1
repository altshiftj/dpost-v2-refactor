param (
    [string]$TaskName,        # Optional custom name for the scheduled task
    [string]$ExePath,         # Optional path to the executable to run
    [string]$LogDir,          # Optional directory where logs will be stored
    [string]$StartIn          # Optional working directory for the process (defaults to EXE folder)
)

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
    $ExePath = Get-ChildItem "$defaultDir\wd-*.exe" -File |
               Sort-Object LastWriteTime -Descending |
               Select-Object -First 1 |
               ForEach-Object { $_.FullName }

    if (-not $ExePath) {
        throw "No wd-*.exe found in $defaultDir."
    }
}

# Paths, names
$ExePath = (Resolve-Path -LiteralPath $ExePath).Path
$ExeDir  = Split-Path $ExePath -Parent
$ExeName = [IO.Path]::GetFileNameWithoutExtension($ExePath)

if (-not $TaskName) { $TaskName = "IPAT-Watchdog-$ExeName" }
if (-not $StartIn)  { $StartIn  = $ExeDir }

# ─────────────────────────────────────────────────────
# Set up log file path and rotate existing
# ─────────────────────────────────────────────────────
if (-not $LogDir) { $LogDir = Join-Path $ExeDir 'logs' }
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$LogPath = Join-Path $LogDir "$TaskName.log"

if (Test-Path $LogPath) {
    $ts         = Get-Date -Format 'yyyyMMdd-HHmmss'
    $base       = [IO.Path]::GetFileNameWithoutExtension($LogPath)
    $ext        = [IO.Path]::GetExtension($LogPath)
    $backupName = "$base-$ts$ext"
    Rename-Item -Path $LogPath -NewName $backupName -Force
}

# ─────────────────────────────────────────────────────
# Remove any existing scheduled task and kill process
# ─────────────────────────────────────────────────────
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask       -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Start-Sleep 2
}

Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $ExePath } |
    Stop-Process -Force

# ─────────────────────────────────────────────────────
# Define the scheduled task components
#   - Use WorkingDirectory = $StartIn
#   - Wrap execution to capture stdout+stderr into $LogPath
# ─────────────────────────────────────────────────────
# Note: New-ScheduledTaskAction supports -WorkingDirectory on modern Windows.
$psCmd = @"
& '$ExePath' *> '$LogPath'
"@.Trim()

$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"${psCmd}`"" `
    -WorkingDirectory $StartIn

# Trigger at user logon
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings: restart on failure, prevent concurrent runs
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 9999 `
    -MultipleInstances IgnoreNew

# Run as current user, elevated
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Register and start
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
Start-ScheduledTask -TaskName $TaskName

# ─────────────────────────────────────────────────────
# Display output for user reference
# ─────────────────────────────────────────────────────
Write-Host "`nRegistered task: $TaskName"
Write-Host "EXE : $ExePath"
Write-Host "StartIn : $StartIn"
Write-Host "Log : $LogPath"
