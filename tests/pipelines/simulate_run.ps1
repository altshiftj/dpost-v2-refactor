# simulate_run.ps1
# Simulate your GitLab "run" stage locally in PowerShell

# --- SETTINGS ---
$plinkPath = "C:\Program Files\PuTTY\plink.exe"
$targetIP = "127.0.0.1"
$targetUser = "testuser"
$targetPass = "password"
$taskName = "IPAT-Watchdog"
$taskScript = "C:\Watchdog\register_task.ps1"

# --- TIMER START ---
$startTime = Get-Date

# --- LOCAL Execution ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Running scheduled task setup locally..."

    if (-Not (Test-Path $taskScript)) {
        Write-Error "$taskScript not found at $taskScript"
        exit 1
    }

    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $taskScript
        Start-ScheduledTask -TaskName $taskName
    } catch {
        Write-Error "Failed to register or start scheduled task locally: $_"
        exit 1
    }

    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Local run simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    exit 0
}

# --- REMOTE Execution ---
if (-Not (Test-Path $plinkPath)) {
    Write-Error "plink.exe not found. Install PuTTY tools or check the path."
    exit 1
}
Write-Host "Found plink.exe. Executing on remote target $targetIP..."

# Register the scheduled task remotely
& $plinkPath -batch -pw "$targetPass" "${targetUser}@${targetIP}" `
    "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Watchdog\register_task.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote task registration failed."
    exit 1
}

# Start the task remotely
& $plinkPath -batch -pw "$targetPass" "${targetUser}@${targetIP}" `
    "powershell -NoProfile -Command Start-ScheduledTask -TaskName '$taskName'"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote task start failed."
    exit 1
}

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "Remote run simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
