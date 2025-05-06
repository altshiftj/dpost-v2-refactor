# simulate_deploy.ps1
. "$PSScriptRoot/env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

$remotePath = 'C:\Watchdog'

$ciJobName  = $env:CI_JOB_NAME
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS

if (-not $ciJobName)  { Write-Error "CI_JOB_NAME not set.";  exit 1 }
if (-not $targetIP)   { $targetIP   = '127.0.0.1'  }
if (-not $targetUser) { $targetUser = 'testuser'   }
if (-not $targetPass) { $targetPass = 'password'   }

$binaryName      = "wd-${ciJobName}.exe"
$distBinaryPath  = "dist\$binaryName"
$exePath         = "$remotePath\$binaryName"
$filesToDeploy   = @($binaryName,'version.txt','infra/windows/register_task.ps1')

if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path 'version.txt'))   { Write-Error "version.txt missing."     ; exit 1 }

"version=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z" | Set-Content -Encoding UTF8 version.txt

$start = Get-Date

if ($targetIP -eq '127.0.0.1') {
    if (!(Test-Path $remotePath)) { New-Item $remotePath -Force -ItemType Directory | Out-Null }

    try {
        Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
        Get-Process | Where-Object { $_.Path -eq $exePath } | Stop-Process -Force
    } catch {}

    foreach ($f in $filesToDeploy[0..1]) {          # exe + txt
        $src = Join-Path $remotePath $f
        if (Test-Path $src) {
            $bak = $src -replace '\.(\w+)$', '_backup.$1'
            if (Test-Path $bak) { Remove-Item $bak -Force }
            Rename-Item -Path $src -NewName $bak -Force
        }
    }
    

    Copy-Item $distBinaryPath                   (Join-Path $remotePath $binaryName)     -Force
    Copy-Item version.txt                       (Join-Path $remotePath 'version.txt')   -Force
    Copy-Item 'infra/windows/register_task.ps1' (Join-Path $remotePath 'register_task.ps1') -Force

    $elapsed = (Get-Date)-$start
    Write-Host "Local deploy done in $($elapsed.ToString('hh\:mm\:ss'))"
    exit 0
}

if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
    Write-Error 'plink / pscp not in PATH.'; exit 1 }

Write-Host "Deploying to $targetIP..."

# Remote script: stop by exact path and backup
$prep = @"
`$p      = '$remotePath'
`$exe    = '$binaryName'
`$path   = Join-Path `$p `$exe

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

#── stop & unregister every IPAT‑Watchdog task
Get-ScheduledTask | Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
    ForEach-Object {
        Stop-ScheduledTask      -TaskName `$_.TaskName -EA SilentlyContinue
        Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false
    }
Start-Sleep 2

#── kill the running exe (exact path match)
Get-Process -EA SilentlyContinue |
    Where-Object { `$_.Path -eq `$path } |
    Stop-Process -Force

#── rename existing files → _backup.ext  (overwrite‑safe)
foreach (`$f in @(`$exe,'version.txt')) {
    `$src = Join-Path `$p `$f
    if (Test-Path `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        if (Test-Path `$bak) { Remove-Item `$bak -Force }
        Rename-Item -Path `$src -NewName `$bak -Force
    }
}
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prep))
& plink -batch -pw $targetPass "$targetUser@$targetIP" "powershell -NoProfile -EncodedCommand $encoded"

if ($LASTEXITCODE) { Write-Error 'Remote prep failed.'; exit 1 }

# SCP new files
$scpMap = @{
    $distBinaryPath                    = "$remotePath/$binaryName"
    'version.txt'                      = "$remotePath/version.txt"
    'infra/windows/register_task.ps1' = "$remotePath/register_task.ps1"
}
foreach ($pair in $scpMap.GetEnumerator()) {
    $dst = $pair.Value -replace '\\','/'
    & pscp -batch -pw $targetPass $pair.Key "$targetUser@${targetIP}:$dst"
    if ($LASTEXITCODE) { Write-Error "SCP of $($pair.Key) failed."; exit 1 }
}

$elapsed = (Get-Date)-$start
Write-Host "Remote deploy complete in $($elapsed.ToString('hh\:mm\:ss'))"
