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

if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path 'version.txt'))   { Write-Error "version.txt missing.";     exit 1 }

@"
COMMIT_TAG=$env:COMMIT_TAG
COMMIT_HASH=$env:COMMIT_HASH
GIT_BRANCH=$env:GIT_BRANCH
BUILD_TIME=$env:BUILD_TIME
DEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z
"@ | Set-Content -Encoding UTF8 version.txt

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

foreach (`$f in @(`$exe,'version.txt')) {
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
    'version.txt'   = "$remotePath/version.txt"
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
