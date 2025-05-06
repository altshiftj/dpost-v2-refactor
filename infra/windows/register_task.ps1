param (
    [string]$TaskName,
    [string]$ExePath,
    [string]$LogDir
)

# ───────────── Admin and Strict Mode ─────────────
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script must be run as Administrator. Exiting."
    exit 1
}

# ───────────── Resolve Executable ─────────────
$defaultDir = "C:\Watchdog"

if (-not $ExePath) {
    $ExePath = Get-ChildItem "$defaultDir\wd-*.exe" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 |
        ForEach-Object { $_.FullName }

    if (-not $ExePath) {
        throw "No wd-*.exe found in $defaultDir. Cannot continue."
    }
}

$ExeDir  = Split-Path $ExePath -Parent
$ExeName = [System.IO.Path]::GetFileNameWithoutExtension($ExePath)

if (-not $TaskName) {
    $TaskName = "IPAT-Watchdog-$ExeName"
}

if (-not $LogDir) {
    $LogDir = Join-Path $ExeDir "logs"
}
$LogPath = Join-Path $LogDir "$TaskName.log"

# ───────────── Kill Old Process + Clean Task ─────────────
try {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Warning "Could not clean up old scheduled task: $_"
}

Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -eq $ExePath
} | ForEach-Object {
    Write-Host "Killing leftover process PID=$($_.Id)"
    $_ | Stop-Process -Force
    Start-Sleep -Milliseconds 500
}

# ───────────── Prepare Logging ─────────────
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
if (Test-Path $LogPath) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Rename-Item $LogPath "$LogPath.$timestamp" -Force
}

# ───────────── Task Setup ─────────────
$RestartInterval = New-TimeSpan -Minutes 1
$RestartCount    = 9999

$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Push-Location '$ExeDir'; & '$ExePath' *> '$LogPath'; Pop-Location`""

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartInterval $RestartInterval `
    -RestartCount $RestartCount `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal `
    -Force

# Optional: Start immediately
Start-ScheduledTask -TaskName $TaskName

Write-Host "`n✅ Registered task: $TaskName"
Write-Host " → EXE: $ExePath"
Write-Host " → Log: $LogPath"
