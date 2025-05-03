# simulate_rollback.ps1

$taskName = "IPAT-Watchdog"
$path = "C:\Watchdog"

Write-Host "Stopping scheduled task..."
try {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
} catch {}

if (Test-Path "$path\run_backup.exe") {
    Copy-Item -Force "$path\run_backup.exe" "$path\run.exe"
    Write-Host "Restored run.exe from backup."
} else {
    Write-Warning "No run_backup.exe found."
}

if (Test-Path "$path\version_backup.txt") {
    Copy-Item -Force "$path\version_backup.txt" "$path\version.txt"
    $ver = Get-Content "$path\version.txt"
    Write-Host "Rolled back to version: $ver"
} else {
    Write-Warning "No version backup found."
}

Write-Host "Restarting scheduled task..."
Start-ScheduledTask -TaskName $taskName
