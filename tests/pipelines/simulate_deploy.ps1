<#
    Simulate GitLab “deploy” job locally or remotely
    Handles .exe updates with stop → backup → replace logic
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot/env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

# --- SETTINGS ---------------------------------------------------------
$remotePath = 'C:\Watchdog'

$ciJobName  = $env:CI_JOB_NAME
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS

if (-not $ciJobName)  { $ciJobName  = 'run'        }
if (-not $targetIP)   { $targetIP   = '127.0.0.1'  }
if (-not $targetUser) { $targetUser = 'testuser'   }
if (-not $targetPass) { $targetPass = 'password'   }

$binaryName      = "wd-${ciJobName}.exe"
$distBinaryPath  = "dist\$binaryName"
$filesToDeploy   = @($binaryName,'version.txt','infra/windows/register_task.ps1')

# ── PRE‑CHECKS ────────────────────────────────────────────────────────
if (!(Test-Path $distBinaryPath)) { Write-Error "$distBinaryPath missing."; exit 1 }
if (!(Test-Path 'version.txt'   )) { Write-Error "version.txt missing."  ; exit 1 }

# 🐞 DEBUG: Stamp version.txt with current UTC timestamp
"version=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z" | Set-Content -Encoding UTF8 version.txt

# ── TIMER ─────────────────────────────────────────────────────────────
$start = Get-Date

# ╔════════════════════════ LOCAL ═════════════════════════════════════╗
if ($targetIP -eq '127.0.0.1') {
    if (!(Test-Path $remotePath)) { New-Item $remotePath -Force -ItemType Directory | Out-Null }

    try {
        Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
        Get-Process $ciJobName -ErrorAction SilentlyContinue | Stop-Process -Force
    } catch {}

    foreach ($f in $filesToDeploy[0..1]) {      # only exe + txt need backup
        $src = Join-Path $remotePath $f
        if (Test-Path $src) {
            $bak = $src -replace '\.(\w+)$','_backup.$1'
            Copy-Item $src $bak -Force
        }
    }

    Copy-Item $distBinaryPath                   (Join-Path $remotePath $binaryName)     -Force
    Copy-Item version.txt                       (Join-Path $remotePath 'version.txt')   -Force
    Copy-Item 'infra/windows/register_task.ps1' (Join-Path $remotePath 'register_task.ps1') -Force

    $elapsed = (Get-Date)-$start
    Write-Host "Local deploy done in $($elapsed.ToString('hh\:mm\:ss'))"
    exit 0
}
# ╚════════════════════════════════════════════════════════════════════╝

# ── REMOTE (needs plink + pscp) ───────────────────────────────────────
if (!(Get-Command plink -EA Ignore) -or !(Get-Command pscp -EA Ignore)) {
    Write-Error 'plink / pscp not in PATH.'; exit 1 }

Write-Host "Deploying to $targetIP..."

# 1️⃣  FIRST: stop process + backup existing files on remote ------------
$prep = @"
`$p   = '$remotePath'
`$job = '$ciJobName'
`$exe = '$binaryName'

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

try {
    if (Get-ScheduledTask -TaskName 'IPAT-Watchdog' -EA SilentlyContinue) {
        Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -EA SilentlyContinue
        Start-Sleep 2
    }
    Get-Process `$job -EA SilentlyContinue | Stop-Process -Force
} catch {}

foreach (`$f in @(`$exe,'version.txt')) {
    `$src = Join-Path `$p `$f
    if (Test-Path `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        Copy-Item `$src `$bak -Force
    }
}
"@

$base64 = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prep))

& plink -batch -pw $targetPass `
        "$targetUser@${targetIP}" `
        "powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $base64"

if ($LASTEXITCODE) { Write-Error 'Remote prep failed.'; exit 1 }

# 2️⃣  THEN: upload new files -------------------------------------------
$scpMap = @{
    $distBinaryPath                    = "$remotePath/$binaryName"
    'version.txt'                      = "$remotePath/version.txt"
    'infra/windows/register_task.ps1'  = "$remotePath/register_task.ps1"
}
foreach ($pair in $scpMap.GetEnumerator()) {
    $dst = ($pair.Value -replace '\\','/')
    & pscp -batch -pw $targetPass $pair.Key "$targetUser@${targetIP}:$dst"
    if ($LASTEXITCODE) { Write-Error "SCP of $($pair.Key) failed."; exit 1 }
}

# ── DONE ──────────────────────────────────────────────────────────────
$elapsed = (Get-Date)-$start
Write-Host "Remote deploy complete in $($elapsed.ToString('hh\:mm\:ss'))"
