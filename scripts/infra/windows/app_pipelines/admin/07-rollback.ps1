<#
    Simulate GitLab "rollback" stage
    Reverts .exe and version.txt to previous backups
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# ── CONFIG ────────────────────────────────────────────────────────────
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS
$ciJobName  = $env:CI_JOB_NAME

$taskName   = "IPAT-Watchdog-$ciJobName"
$exe        = "C:\Watchdog\wd-$ciJobName.exe"
$exeBackup  = $exe -replace '\.exe$','_backup.exe'
$verPath    = "C:\Watchdog\version.txt"
$verBackup  = "C:\Watchdog\version_backup.txt"

$start = Get-Date

# ── LOCAL ROLLBACK ────────────────────────────────────────────────────
if ($targetIP -eq '127.0.0.1') {
    Write-Host "Performing local rollback..."

    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

    # Kill leftover processes if running
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe } | ForEach-Object {
        Write-Host "Killing process PID=$($_.Id)"
        Stop-Process -Id $_.Id -Force
        Start-Sleep -Seconds 1
    }

    if (Test-Path $exeBackup) {
        Copy-Item $exeBackup $exe -Force
        Write-Host "Restored EXE: $exe"
    } else {
        Write-Warning "EXE backup not found: $exeBackup"
    }

    if (Test-Path $verBackup) {
        Copy-Item $verBackup $verPath -Force
        Write-Host "Restored version.txt"
        Write-Host "Rolled back to version: $(Get-Content $verPath)"
    } else {
        Write-Warning "version.txt backup not found."
    }

    Start-ScheduledTask -TaskName $taskName
    Write-Host "Local rollback complete."
    exit 0
}

# ── REMOTE ROLLBACK ───────────────────────────────────────────────────
if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH. Aborting."
    exit 1
}

Write-Host "Performing remote rollback on $targetIP..."

$rollbackScript = @"
`$task    = '$taskName'
`$exe     = '$exe'
`$bak     = '$exeBackup'
`$ver     = '$verPath'
`$verBak  = '$verBackup'

try {
    if (Get-ScheduledTask -TaskName `$task -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName `$task -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    Get-Process -ErrorAction SilentlyContinue | Where-Object { `$_.Path -eq `$exe } | ForEach-Object {
        Write-Host "Killing process PID=$($_.Id)"
        Stop-Process -Id `$_.Id -Force
        Start-Sleep -Seconds 1
    }

    Write-Host "Checking for EXE backup at: `$bak"
    if (Test-Path `$bak) {
        Copy-Item -Force `$bak `$exe
        Write-Host "Restored EXE"
    } else {
        Write-Host "EXE backup not found"
    }

    Write-Host "Checking for version backup at: `$verBak"
    if (Test-Path `$verBak) {
        Copy-Item -Force `$verBak `$ver
        Write-Host "Restored version.txt"
        Get-Content `$ver
    } else {
        Write-Host "version.txt backup not found"
    }

    Start-ScheduledTask -TaskName `$task
    Write-Host "Remote rollback complete."
} catch {
    Write-Host "Rollback failed:"
    Write-Host `$_.Exception.Message
    exit 1
}
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($rollbackScript))
$command = "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded"

& plink -batch -pw "$targetPass" "$targetUser@$targetIP" $command

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote rollback failed."
    exit 1
}

$elapsed = (Get-Date) - $start
Write-Host ("Rollback completed in {0:hh\:mm\:ss}" -f $elapsed)
