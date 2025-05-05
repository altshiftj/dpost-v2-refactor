. "$PSScriptRoot\env.ps1"

# simulate_run.ps1
# Simulate your GitLab "run" stage locally in PowerShell

try {
    # --- SETTINGS ---
    $plinkPath = "C:\Program Files\PuTTY\plink.exe"

    # Environment-driven values (like GitLab CI)
    $targetIP   = $env:TARGET_IP
    $targetUser = $env:TARGET_USER
    $targetPass = $env:TARGET_PASS
    $ciJobName  = $env:CI_JOB_NAME

    # Fallback defaults for local testing
    if (-not $targetIP)   { $targetIP = "127.0.0.1" }
    if (-not $targetUser) { $targetUser = "testuser" }
    if (-not $targetPass) { $targetPass = "password" }
    if (-not $ciJobName)  { $ciJobName = "sem_tischrem_blb" }

    $taskName     = "IPAT-Watchdog-$ciJobName"
    $exePath      = "C:\Watchdog\wd-${ciJobName}.exe"
    $currentUser  = "$env:USERDOMAIN\$env:USERNAME"

    # --- Elevate only if needed (local run) ---
    if ($targetIP -eq "127.0.0.1") {
        if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)) {
            Write-Warning "Local task setup requires admin. Relaunching with elevation..."
            Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
            exit
        }
    }

    # --- TIMER START ---
    $startTime = Get-Date

    # --- LOCAL Execution ---
    if ($targetIP -eq "127.0.0.1") {
        Write-Host "Running scheduled task setup locally..."

        if (-Not (Test-Path $exePath)) {
            throw "$exePath not found! Make sure deployment ran."
        }

        $action    = New-ScheduledTaskAction -Execute $exePath
        $trigger   = New-ScheduledTaskTrigger -AtStartup
        $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Password -RunLevel Highest

        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force
        Start-ScheduledTask -TaskName $taskName

        $endTime = Get-Date
        $duration = $endTime - $startTime
        Write-Host "Local run simulation complete."
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
        Read-Host "Press Enter to exit"
        exit 0
    }

    # --- REMOTE Execution ---
    if (-Not (Test-Path $plinkPath)) {
        throw "plink.exe not found. Install PuTTY tools or check the path: $plinkPath"
    }

    Write-Host "Performing remote run task setup on $targetIP..."

    & $plinkPath -batch -pw "$targetPass" "$targetUser@$targetIP" `
        "powershell -Command `" `
        `$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name; `
        `$a=New-ScheduledTaskAction -Execute '$exePath'; `
        `$t=New-ScheduledTaskTrigger -AtStartup; `
        `$p=New-ScheduledTaskPrincipal -UserId `$currentUser -LogonType Password -RunLevel Highest; `
        Register-ScheduledTask -TaskName '$taskName' -Action `$a -Trigger `$t -Principal `$p -Force; `
        Start-ScheduledTask -TaskName '$taskName'`""

    if ($LASTEXITCODE -ne 0) {
        throw "Remote task registration or start failed (exit code $LASTEXITCODE)."
    }

    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Remote run simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    Read-Host "Press Enter to exit"
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nScript failed. Please review the error above."
    Read-Host "Press Enter to exit"
    exit 1
}
