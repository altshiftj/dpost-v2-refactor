<#
    Rollback deployment via router SSH hop
    - SSH to router, then SSH from router to Windows PC
    - Restore previous backup files
    - Restart services
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# ── CONFIG ────────────────────────────────────────────────────────────
$routerIP   = $env:ROUTER_IP
$targetIP   = $env:TARGET_IP
$ciJobName  = $env:CI_JOB_NAME

$taskName   = "IPAT-Watchdog-$ciJobName"
$exe        = "$env:REMOTE_PATH\wd-$ciJobName.exe"
$exeBackup  = $exe -replace '\.exe$','_backup.exe'
# Adopt job-aware version filenames; keep legacy fallbacks handled in remote script
$verPath    = "$env:REMOTE_PATH\version-$ciJobName.txt"
$verBackup  = "$env:REMOTE_PATH\version-$ciJobName`_backup.txt"

$start = Get-Date

if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH. Aborting."
    exit 1
}

Write-Host "=== Rollback via Router ==="
Write-Host "Router: $routerIP"
Write-Host "Target: $targetIP"
Write-Host "Rolling back: $ciJobName"

# ── BUILD ROLLBACK SCRIPT ─────────────────────────────────────────────

$rollbackScript = @"
`$task      = '$taskName'
`$exe       = '$exe'
`$bak       = '$exeBackup'
`$verNew    = '$verPath'              # version-<job>.txt
`$verOld    = '$($env:REMOTE_PATH)\version.txt'   # legacy
`$verBakNew = '$verBackup'            # version-<job>_backup.txt
`$verBakOld = '$($env:REMOTE_PATH)\version_backup.txt'  # legacy

Write-Host "=== Starting Rollback Process ==="

try {
    # Stop scheduled task
    Write-Host "Stopping scheduled task: `$task"
    if (Get-ScheduledTask -TaskName `$task -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName `$task -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "✓ Task stopped"
    } else {
        Write-Host "! Task not found: `$task"
    }

    # Kill running processes
    Write-Host "Checking for running processes..."
    Get-Process -ErrorAction SilentlyContinue | Where-Object { `$_.Path -eq `$exe } | ForEach-Object {
        Write-Host "Killing process PID=`$(`$_.Id) (`$(`$_.ProcessName))"
        Stop-Process -Id `$_.Id -Force
        Start-Sleep -Seconds 1
    }

    # Restore executable
    Write-Host "Restoring executable..."
    Write-Host "Backup location: `$bak"
    if (Test-Path `$bak) {
        Copy-Item -Force `$bak `$exe
        Write-Host "✓ Executable restored: `$exe"
        
        # Verify restored file
        if (Test-Path `$exe) {
            `$size = (Get-Item `$exe).Length
            `$sizeMB = [math]::Round(`$size / 1MB, 2)
            Write-Host "  Size: `$sizeMB MB"
        }
    } else {
        Write-Host "✗ Executable backup not found: `$bak"
    }

    # Restore version file (prefer job-aware, fallback to legacy)
    Write-Host "Restoring version file..."
    `$chosenBak = `$null
    if (Test-Path `$verBakNew) {
        `$chosenBak = `$verBakNew
    } elseif (Test-Path `$verBakOld) {
        `$chosenBak = `$verBakOld
    }

    if (`$chosenBak) {
        # Always restore into the job-aware name going forward
        Copy-Item -Force `$chosenBak `$verNew
        Write-Host "✓ Version file restored -> `$verNew"
        if (Test-Path `$verNew) {
            Write-Host "Previous version info:"
            Get-Content `$verNew | ForEach-Object { Write-Host "  `$_" }
        }
    } else {
        Write-Host "✗ No version backup found (checked:`n  `$verBakNew`n  `$verBakOld)"
    }

    # Restart scheduled task
    Write-Host "Restarting scheduled task..."
    if (Get-ScheduledTask -TaskName `$task -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName `$task
        Start-Sleep -Seconds 2
        
        `$taskInfo = Get-ScheduledTaskInfo -TaskName `$task
        Write-Host "✓ Task restarted"
        Write-Host "  State: `$(Get-ScheduledTask -TaskName `$task | Select-Object -ExpandProperty State)"
        Write-Host "  Last Result: `$(`$taskInfo.LastTaskResult)"
    } else {
        Write-Host "! Cannot restart task - not found: `$task"
    }

    Write-Host "✓ Rollback completed successfully"

} catch {
    Write-Host "✗ Rollback failed:"
    Write-Host `$_.Exception.Message
    exit 1
}
"@

# ── EXECUTE ROLLBACK VIA DOUBLE SSH ───────────────────────────────────
Write-Host "`nExecuting rollback via double SSH hop..."

$encodedRollback = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($rollbackScript))
$windowsCommand = "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encodedRollback"
$doubleSSHCommand = Get-DoubleSSHCommand -WindowsCommand $windowsCommand

$routerArgs = Get-RouterSSHCommand -Command $doubleSSHCommand
& plink.exe @routerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote rollback failed (exit code $LASTEXITCODE)"
    exit 1
}

# ── VERIFY ROLLBACK ───────────────────────────────────────────────────
Write-Host "`nVerifying rollback..."

$verifyScript = @"
`$exe  = '$exe'
`$verN = '$verPath'
`$verO = '$($env:REMOTE_PATH)\version.txt'
`$task = '$taskName'

Write-Host "=== Rollback Verification ==="

if (Test-Path `$exe) {
    `$fileInfo = Get-Item `$exe
    `$sizeMB = [math]::Round(`$fileInfo.Length / 1MB, 2)
    Write-Host "✓ Executable exists: `$exe (`$sizeMB MB)"
    Write-Host "  Modified: `$(`$fileInfo.LastWriteTime)"
} else {
    Write-Host "✗ Executable missing: `$exe"
}

`$verToShow = if (Test-Path `$verN) { `$verN } elseif (Test-Path `$verO) { `$verO } else { `$null }
if (`$verToShow) {
    Write-Host "✓ Version file exists: `$verToShow"
    Write-Host "Current version:"
    Get-Content `$verToShow | ForEach-Object { Write-Host "  `$_" }
} else {
    Write-Host "✗ Version file missing: `$verN (and legacy `$verO)"
}

try {
    `$taskState = (Get-ScheduledTask -TaskName `$task).State
    Write-Host "✓ Task state: `$taskState"
} catch {
    Write-Host "✗ Task not found: `$task"
}

Write-Host "=== Verification Complete ==="
"@

$encodedVerify = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($verifyScript))
$verifyCommand = "powershell -NoProfile -EncodedCommand $encodedVerify"
$doubleSSHVerify = Get-DoubleSSHCommand -WindowsCommand $verifyCommand

$verifyArgs = Get-RouterSSHCommand -Command $doubleSSHVerify
& plink.exe @verifyArgs

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Rollback verification had issues, but rollback may have succeeded"
}

# ── COMPLETION ─────────────────────────────────────────────────────────
$elapsed = (Get-Date) - $start
Write-Host "`n=== Rollback Complete ==="
Write-Host "Target: $targetIP (via router $routerIP)"
Write-Host ("Total time: {0:hh\:mm\:ss}" -f $elapsed)
