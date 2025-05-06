param (
    [string]$TaskName,
    [string]$ExePath,
    [string]$LogDir
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Run this script as Administrator."
    exit 1
}

# ---------- resolve executable ----------
$defaultDir = "C:\Watchdog"

if (-not $ExePath) {
    $ExePath = Get-ChildItem "$defaultDir\wd-*.exe" -File |
               Sort-Object LastWriteTime -Descending |
               Select-Object -First 1 |
               ForEach-Object { $_.FullName }

    if (-not $ExePath) { throw "No wd-*.exe found in $defaultDir." }
}

$ExeDir  = Split-Path $ExePath -Parent
$ExeName = [IO.Path]::GetFileNameWithoutExtension($ExePath)

if (-not $TaskName) { $TaskName = "IPAT-Watchdog-$ExeName" }

# ---------- log path ----------
if (-not $LogDir) { $LogDir = Join-Path $ExeDir 'logs' }
$LogPath = Join-Path $LogDir "$TaskName.log"

# ---------- kill old task / process ----------
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask      -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Start-Sleep 2
}

Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $ExePath } |
    Stop-Process -Force

# ---------- prepare logging ----------
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

if (Test-Path $LogPath) {
    $ts         = Get-Date -Format 'yyyyMMdd-HHmmss'
    $base       = [IO.Path]::GetFileNameWithoutExtension($LogPath)
    $ext        = [IO.Path]::GetExtension($LogPath)          # ".log"
    $backupName = "$base-$ts$ext"                            # watchdog‑20250506‑164903.log
    Rename-Item -Path $LogPath -NewName $backupName -Force
}

# ---------- scheduled‑task definition ----------
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"& { Push-Location '$ExeDir'; & '$ExePath' *> '$LogPath'; Pop-Location }`""

$Trigger   = New-ScheduledTaskTrigger -AtLogOn
$Settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 9999 -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
Start-ScheduledTask   -TaskName $TaskName

Write-Host "`nRegistered task: $TaskName"
Write-Host "EXE : $ExePath"
Write-Host "Log : $LogPath"
