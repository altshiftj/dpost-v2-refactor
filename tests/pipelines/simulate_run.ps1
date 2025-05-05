# simulate_run.ps1
# Simulate GitLab CI "run" stage using remote execution via plink

. "$PSScriptRoot\env.ps1"

try {
    # --- SETTINGS ---
    $plinkPath = "C:\Program Files\PuTTY\plink.exe"

    # Load environment-driven values
    $targetIP   = $env:TARGET_IP
    $targetUser = $env:TARGET_USER
    $targetPass = $env:TARGET_PASS
    $ciJobName  = $env:CI_JOB_NAME

    # Fallbacks for testing
    if (-not $targetIP)   { $targetIP = "127.0.0.1" }
    if (-not $targetUser) { $targetUser = "testuser" }
    if (-not $targetPass) { $targetPass = "password" }
    if (-not $ciJobName)  { $ciJobName = "run" }

    $taskName = "IPAT-Watchdog-$ciJobName"
    $exePath  = "C:\Watchdog\wd-${ciJobName}.exe"

    # --- Ensure plink is available ---
    if (-not (Test-Path $plinkPath)) {
        throw "plink.exe not found at: $plinkPath"
    }

    # --- TIMER START ---
    $startTime = Get-Date
    Write-Host "Performing remote run task setup on $targetIP as $targetUser..."

    # --- Build the remote command ---
    $remoteScriptLines = @(
        "`$a = New-ScheduledTaskAction -Execute '$exePath';",
        "`$t = New-ScheduledTaskTrigger -AtLogon;",
        "`$p = New-ScheduledTaskPrincipal -UserId '$targetUser' -LogonType Password -RunLevel Highest;",
        "Register-ScheduledTask -TaskName '$taskName' -Action `$a -Trigger `$t -Principal `$p -Force;",
        "Start-ScheduledTask -TaskName '$taskName';",
        "`n'Task state:';",
        "Get-ScheduledTask -TaskName '$taskName' | Get-ScheduledTaskInfo | Format-List *"
    )
    $remoteScript = ($remoteScriptLines -join ' ')
    $cmd = "powershell -NoProfile -Command `"$remoteScript`""

    # --- Fire the command over SSH ---
    & $plinkPath -batch -pw "$targetPass" "$targetUser@$targetIP" $cmd

    if ($LASTEXITCODE -ne 0) {
        throw "Remote task registration or start failed (exit code $LASTEXITCODE)."
    }

    # --- TIMER END ---
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Remote run simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    Read-Host "Press Enter to exit"
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
