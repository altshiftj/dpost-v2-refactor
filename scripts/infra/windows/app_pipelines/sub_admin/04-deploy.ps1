. "$PSScriptRoot/00-env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../../../../..")

$remotePath   = $env:REMOTE_DIR
$ciJobName    = $env:CI_JOB_NAME
$targetIP     = $env:TARGET_IP
$targetUser   = $env:TARGET_USER
$targetPass   = $env:TARGET_PASS
$sshPort      = $env:SSH_PORT
$sshHostKey   = $env:SSH_HOSTKEY

if (-not $ciJobName)  { Write-Error "CI_JOB_NAME not set.";  exit 1 }

$binaryName      = "wd-${ciJobName}.exe"
$distBinaryPath  = "dist\$binaryName"
$buildVersionPath      = "build\version-$ciJobName.txt"
$deployVersionFilename = "version-$ciJobName.txt"
$deployVersionPath     = $deployVersionFilename

if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path $buildVersionPath)) {
    Write-Error "$buildVersionPath missing. Did you run the build?"
    exit 1
}

$deployMeta = @"
DEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z
CI_JOB_NAME=$env:CI_JOB_NAME
DEVICE_PLUGINS=$env:DEVICE_PLUGINS
PIP_EXTRAS=$env:PIP_EXTRAS
"@
(Get-Content $buildVersionPath) + $deployMeta | Set-Content -Encoding UTF8 $deployVersionPath

$start = Get-Date

# ── REMOTE DEPLOY ───────────────────────────────────────────────
if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
    Write-Error 'plink / pscp not in PATH.'; exit 1 }

Write-Host "Deploying to $targetIP..."

# Remote prep script
$prep = @"
`$ErrorActionPreference = 'Stop'
`$p      = '$remotePath'
`$exe    = '$binaryName'
`$path   = Join-Path `$p `$exe

if (!(Test-Path -LiteralPath `$p)) {
    New-Item -ItemType Directory -Path `$p -Force -ErrorAction Stop | Out-Null
}

# Sanity check: ensure target dir exists before proceeding
if (!(Test-Path -LiteralPath `$p)) {
    throw "Remote target path not found or not creatable: `$p"
}

# Stop watchdog tasks/processes before rotating files to avoid file locks.
if (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue) {
    Get-ScheduledTask -ErrorAction SilentlyContinue |
        Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
        ForEach-Object {
            Stop-ScheduledTask       -TaskName `$_.TaskName -EA SilentlyContinue
            Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false -EA SilentlyContinue
        }
}
Start-Sleep 2
Get-Process -EA SilentlyContinue |
    Where-Object { `$_.Path -eq `$path } |
    Stop-Process -Force

foreach (`$f in @(`$exe,'$deployVersionFilename')) {
    `$src = Join-Path `$p `$f
    if (Test-Path -LiteralPath `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        if (Test-Path -LiteralPath `$bak) { Remove-Item -LiteralPath `$bak -Force }
        Rename-Item -LiteralPath `$src -NewName `$bak -Force
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
    $distBinaryPath = "$remotePath/$binaryName"
    $deployVersionPath = "$remotePath/$deployVersionFilename"
}
foreach ($pair in $scpMap.GetEnumerator()) {
    # Keep a native Windows path and quote it
    $dstWin = $pair.Value

    $scpArgs = @(
        "-batch", "-P", $sshPort, "-pw", $targetPass,
        "-hostkey", $sshHostKey,
        "-scp",                                  # <— force SCP protocol
        $pair.Key, "$targetUser@${targetIP}:`"$dstWin`""
    )
    & pscp.exe @scpArgs
    if ($LASTEXITCODE) { Write-Error "SCP of $($pair.Key) failed."; exit 1 }
}


$elapsed = (Get-Date) - $start
Write-Host "Remote deploy complete in $($elapsed.ToString('hh\:mm\:ss'))"
