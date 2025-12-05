# simulate_deploy.ps1
. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

$remotePath   = 'C:\Watchdog'
$ciJobName    = $env:CI_JOB_NAME
$targetIP     = $env:TARGET_IP
$targetUser   = $env:TARGET_USER
$targetPass   = $env:TARGET_PASS
$sshPort      = $env:SSH_PORT
$sshHostKey   = $env:SSH_HOSTKEY

$binaryName      = "wd-${ciJobName}.exe"
$distBinaryPath  = "dist\$binaryName"
$exePath         = Join-Path $remotePath $binaryName
$buildVersionPath      = "build\version-$ciJobName.txt"
$deployVersionFilename = "version-$ciJobName.txt"
$deployVersionPath     = $deployVersionFilename
$filesToDeploy   = @($binaryName, $deployVersionFilename, 'scripts\infra\windows\utils\register_task.ps1')

if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path $buildVersionPath))   { Write-Error "$buildVersionPath missing. Did you run the build?"; exit 1 }

$deployMeta = @"
DEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z
CI_JOB_NAME=$env:CI_JOB_NAME
DEVICE_PLUGINS=$env:DEVICE_PLUGINS
PIP_EXTRAS=$env:PIP_EXTRAS
"@
(Get-Content $buildVersionPath) + $deployMeta | Set-Content -Encoding UTF8 $deployVersionPath


$start = Get-Date

# ── LOCAL DEPLOY ───────────────────────────────────────────────
if ($targetIP -eq '127.0.0.1') {
    if (!(Test-Path $remotePath)) { New-Item $remotePath -Force -ItemType Directory | Out-Null }

    try {
        Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
        Get-Process | Where-Object { $_.Path -eq $exePath } | Stop-Process -Force
    } catch {}

    foreach ($f in $filesToDeploy[0..1]) {
        $src = Join-Path $remotePath $f
        if (Test-Path $src) {
            $bak = $src -replace '\.(\w+)$', '_backup.$1'
            if (Test-Path $bak) { Remove-Item $bak -Force }
            Rename-Item -Path $src -NewName $bak -Force
        }
    }

    Copy-Item $distBinaryPath                           (Join-Path $remotePath $binaryName)     -Force
    Copy-Item version.txt                               (Join-Path $remotePath 'version.txt')   -Force
    Copy-Item 'scripts/infra/windows/utils/register_task.ps1' (Join-Path $remotePath 'register_task.ps1') -Force

    $elapsed = (Get-Date) - $start
    Write-Host "Local deploy done in $($elapsed.ToString('hh\:mm\:ss'))"
    exit 0
}

# ── REMOTE DEPLOY ───────────────────────────────────────────────
if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
    Write-Error 'plink / pscp not in PATH.'; exit 1 }

Write-Host "Deploying to $targetIP..."

# Remote prep script
$prep = @"
`$p      = '$remotePath'
`$exe    = '$binaryName'
`$path   = Join-Path `$p `$exe

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

Get-ScheduledTask | Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
    ForEach-Object {
        Stop-ScheduledTask       -TaskName `$_.TaskName -EA SilentlyContinue
        Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false
    }
Start-Sleep 2

Get-Process -EA SilentlyContinue |
    Where-Object { `$_.Path -eq `$path } |
    Stop-Process -Force

foreach (`$f in @(`$exe,'version.txt')) {
    `$src = Join-Path `$p `$f
    if (Test-Path `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        if (Test-Path `$bak) { Remove-Item `$bak -Force }
        Rename-Item -Path `$src -NewName `$bak -Force
    }
}
"@

# Encode and invoke via SSH
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prep))
$plinkArgs = @(
    "-batch", "-P", $sshPort, "-pw", $targetPass,
    "-hostkey", $sshHostKey,
    "$targetUser@$targetIP",
    "powershell -NoProfile -EncodedCommand $encoded"
)
& plink.exe @plinkArgs
if ($LASTEXITCODE) { Write-Error 'Remote prep failed.'; exit 1 }

# SCP new files
$scpMap = @{
    $distBinaryPath                          = "$remotePath/$binaryName"
    'version.txt'                            = "$remotePath/version.txt"
    'scripts\infra\windows\utils\register_task.ps1'= "$remotePath/register_task.ps1"
}
foreach ($pair in $scpMap.GetEnumerator()) {
    $dst = $pair.Value -replace '\\','/'
    $scpArgs = @(
        "-batch", "-P", $sshPort, "-pw", $targetPass,
        $pair.Key, "$targetUser@${targetIP}:`"$dst`""
    )
    & pscp.exe @scpArgs
    if ($LASTEXITCODE) { Write-Error "SCP of $($pair.Key) failed."; exit 1 }
}

$elapsed = (Get-Date) - $start
Write-Host "Remote deploy complete in $($elapsed.ToString('hh\:mm\:ss'))"
