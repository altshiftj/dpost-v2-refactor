# simulate_run.ps1
# Simulate your GitLab "run" stage locally in PowerShell

# --- SETTINGS ---
$plinkPath = "C:\\Program Files\\PuTTY\\plink.exe"  # Adjust if different
$targetIP = "127.0.0.1"
$targetUser = "testuser"
$targetPass = "password"
$taskName = "IPAT-Watchdog"

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: LOCAL run if on 127.0.0.1 ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Running scheduled task setup locally..."

    # Register the scheduled task locally
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\\Watchdog\\register_task.ps1"

    # Start the task immediately
    Start-ScheduledTask -TaskName $taskName

    # --- TIMER END ---
    $endTime = Get-Date
    $duration = $endTime - $startTime

    Write-Host "Local run simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration) #-ForegroundColor Green
    exit 0
}

# --- Step 2: REMOTE SSH if real target ---
if (-Not (Test-Path $plinkPath)) {
    Write-Error "plink.exe not found. Install PuTTY tools or adjust path."
    exit 1
}
Write-Host "Found plink.exe."

Write-Host "Registering scheduled task remotely..."
& $plinkPath -batch -pw "$targetPass" "${targetUser}@${targetIP}" "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Watchdog\\register_task.ps1"

Write-Host "Starting scheduled task '$taskName' remotely..."
& $plinkPath -batch -pw "$targetPass" "${targetUser}@${targetIP}" "powershell -NoProfile -Command Start-ScheduledTask -TaskName '${taskName}'"

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "Run simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration) #-ForegroundColor Green
