# ── ENV + CONFIG ──────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../../../..")

$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS
$ciJobName  = $env:CI_JOB_NAME

$exe        = "C:\Watchdog\wd-$ciJobName.exe"
$exeBackup  = $exe -replace '\.exe$','_backup.exe'
$verPath    = "C:\Watchdog\version.txt"
$verBackup  = "C:\Watchdog\version_backup.txt"

$start = Get-Date

# ── REMOTE ROLLBACK (RENAME ONLY) ─────────────────────────────────────
if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH. Aborting."
    exit 1
}

Write-Host "Performing remote rollback (rename only) on $targetIP..."

$rollbackScript = @"
`$exe     = '$exe'
`$bak     = '$exeBackup'
`$ver     = '$verPath'
`$verBak  = '$verBackup'
`$proc    = 'wd-$ciJobName'

try {
    # Stop the process if running
    `$procObj = Get-Process -Name `$proc -ErrorAction SilentlyContinue
    if (`$procObj) {
        Stop-Process -Name `$proc -Force
        Write-Host "Stopped process: `$proc"
    }

    if (Test-Path `$bak) {
        if (Test-Path `$exe) { Remove-Item `$exe -Force }
        Rename-Item -Path `$bak -NewName (Split-Path `$exe -Leaf)
        Write-Host "Renamed backup to original EXE"
    } else {
        Write-Host "EXE backup not found"
    }

    if (Test-Path `$verBak) {
        if (Test-Path `$ver) { Remove-Item `$ver -Force }
        Rename-Item -Path `$verBak -NewName (Split-Path `$ver -Leaf)
        Write-Host "Renamed backup to original version.txt"
    } else {
        Write-Host "version.txt backup not found"
    }
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
