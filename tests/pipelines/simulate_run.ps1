# simulate_run.ps1
# Simulate GitLab CI "run" stage using remote execution via plink and register_task.ps1

. "$PSScriptRoot\env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

try {
    # --- SETTINGS ---
    $plinkPath = "C:\Program Files\PuTTY\plink.exe"

    # Load environment-driven values
    $targetIP   = $env:TARGET_IP
    $targetUser = $env:TARGET_USER
    $targetPass = $env:TARGET_PASS
    $ciJobName  = $env:CI_JOB_NAME

    # Fallbacks for local testing
    if (-not $targetIP)   { $targetIP = "127.0.0.1" }
    if (-not $targetUser) { $targetUser = "testuser" }
    if (-not $targetPass) { $targetPass = "password" }
    if (-not $ciJobName)  { $ciJobName = "run" }

    # Define task name and exe path for this job
    $taskName = "IPAT-Watchdog-$ciJobName"
    $exePath  = "C:\Watchdog\wd-$ciJobName.exe"

    # --- Ensure plink is available ---
    if (-not (Test-Path $plinkPath)) {
        throw "plink.exe not found at: $plinkPath"
    }

    # --- TIMER START ---
    $startTime = Get-Date
    Write-Host "Registering task '$taskName' on $targetIP as $targetUser..."

    # --- Build command to call register_task.ps1 with parameters ---
    $remoteScript = @(
        "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Watchdog\register_task.ps1",
        "-TaskName `"$taskName`"",
        "-ExePath `"$exePath`""
    ) -join " "

    # --- Fire the command over SSH ---
    & $plinkPath -batch -pw "$targetPass" "$targetUser@$targetIP" $remoteScript

    if ($LASTEXITCODE -ne 0) {
        throw "Remote task registration failed (exit code $LASTEXITCODE)."
    }

    # --- TIMER END ---
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "`nRemote run task setup complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    Read-Host "Press Enter to exit"
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
