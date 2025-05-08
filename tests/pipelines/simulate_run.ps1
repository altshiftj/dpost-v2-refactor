<#
    Simulate GitLab "run" job by remotely registering a scheduled task
    via plink and the remote register_task.ps1 script
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot/env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

# --- SETTINGS ---------------------------------------------------------
$ciJobName   = $env:CI_JOB_NAME
$targetIP    = $env:TARGET_IP
$targetUser  = $env:TARGET_USER
$targetPass  = $env:TARGET_PASS
$sshPort     = $env:SSH_PORT
$sshHostKey  = $env:SSH_HOSTKEY

if (-not $ciJobName)  { $ciJobName  = 'run'        }
if (-not $targetIP)   { $targetIP   = '127.0.0.1'  }
if (-not $targetUser) { $targetUser = 'testuser'   }
if (-not $targetPass) { $targetPass = 'password'   }

$taskName = "IPAT-Watchdog-$ciJobName"
$exePath  = "C:\Watchdog\wd-$ciJobName.exe"

# ── TOOL CHECK ────────────────────────────────────────────────────────
if (!(Get-Command plink -ErrorAction SilentlyContinue)) {
    Write-Error "plink not found in PATH. Add PuTTY to your environment variables."
    exit 1
}

# ── TIMER START ───────────────────────────────────────────────────────
$startTime = Get-Date
Write-Host "Registering task '$taskName' on $targetIP..."

# ── BUILD REMOTE COMMAND ──────────────────────────────────────────────
$remoteCmd = @(
    'powershell',
    '-NoProfile',
    '-ExecutionPolicy Bypass',
    '-File', 'C:\Watchdog\register_task.ps1',
    '-TaskName', "`"$taskName`"",
    '-ExePath',  "`"$exePath`""
) -join ' '

# ── EXECUTE OVER SSH ──────────────────────────────────────────────────
$plinkArgs = @(
    '-batch',
    '-P', $sshPort,
    '-pw', $targetPass,
    '-hostkey', $sshHostKey,
    "$targetUser@$targetIP",
    $remoteCmd
)
& plink.exe @plinkArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote task registration failed (exit code $LASTEXITCODE)"
    exit 1
}

# ── TIMER END ─────────────────────────────────────────────────────────
$duration = (Get-Date) - $startTime
Write-Host "`nRemote task registration complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
