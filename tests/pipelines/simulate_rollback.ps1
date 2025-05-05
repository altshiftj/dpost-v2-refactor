. "$PSScriptRoot\env.ps1"

# simulate_rollback.ps1
# Simulate GitLab rollback stage locally or remotely

# --- SETTINGS ---
$plinkPath = "C:\Program Files\PuTTY\plink.exe"

# Load env vars (or fallbacks)
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS
$ciJobName  = $env:CI_JOB_NAME

if (-not $targetIP)   { $targetIP = "127.0.0.1" }
if (-not $targetUser) { $targetUser = "testuser" }
if (-not $targetPass) { $targetPass = "password" }
if (-not $ciJobName)  { $ciJobName = "run" }

$taskName = "IPAT-Watchdog-$ciJobName"
$exe      = "C:\Watchdog\wd_${ciJobName}.exe"
$exeBackup = "${exe}_backup"

# --- TIMER START ---
$startTime = Get-Date

# --- LOCAL Rollback ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Performing local rollback..."

    try {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    } catch {
        Write-Warning "Could not stop scheduled task: $taskName"
    }

    if (Test-Path $exeBackup) {
        Copy-Item -Force $exeBackup $exe
        Write-Host "Restored $exe from backup."
    } else {
        Write-Warning "Backup not found: $exeBackup"
    }

    $versionBackup = "C:\Watchdog\version_backup.txt"
    $versionPath   = "C:\Watchdog\version.txt"

    if (Test-Path $versionBackup) {
        Copy-Item -Force $versionBackup $versionPath
        Write-Host "Restored version.txt"
        $ver = Get-Content $versionPath
        Write-Host "Rolled back to version: $ver"
    } else {
        Write-Warning "No version backup found."
    }

    Start-ScheduledTask -TaskName $taskName
    Write-Host "Local rollback complete."
    exit 0
}

# --- REMOTE Rollback ---
if (-not (Test-Path $plinkPath)) {
    Write-Error "plink.exe not found at $plinkPath"
    exit 1
}

Write-Host "Performing remote rollback on $targetIP..."

& $plinkPath -batch -pw "$targetPass" "$targetUser@$targetIP" `
    "powershell -Command `" `
    Stop-ScheduledTask -TaskName '$taskName' -ErrorAction SilentlyContinue; `
    if (Test-Path '$exeBackup') { Copy-Item '$exeBackup' '$exe' -Force }; `
    if (Test-Path 'C:\Watchdog\version_backup.txt') { `
        Copy-Item 'C:\Watchdog\version_backup.txt' 'C:\Watchdog\version.txt' -Force }; `
    Start-ScheduledTask -TaskName '$taskName'`""

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote rollback failed."
    exit 1
}

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "Remote rollback complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
