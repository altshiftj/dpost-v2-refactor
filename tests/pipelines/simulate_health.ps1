<#
    Simulate GitLab "health" stage by polling a /health endpoint
    Works with Windows PowerShell 5+ and doesn't rely on env.ps1 for optional config
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\env.ps1"  # only loads TARGET_IP and login info
Set-Location -Path (Resolve-Path "$PSScriptRoot\../..")

# ── CONFIG ────────────────────────────────────────────────────────────
$targetIP    = if ($env:TARGET_IP) { $env:TARGET_IP } else { '127.0.0.1' }
$healthPort  = 8001
$healthPath  = '/health'
$maxAttempts = 30
$waitSeconds = 2

$url = "http://$targetIP`:$healthPort$healthPath"

# ── TIMER ─────────────────────────────────────────────────────────────
$startTime = Get-Date
Write-Host "Waiting for service at $url ..."

# ── FUNCTION ──────────────────────────────────────────────────────────
function Test-Health {
    param ([string]$uri)

    try {
        $null = Invoke-RestMethod -Uri $uri -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

# ── HEALTH LOOP ───────────────────────────────────────────────────────
for ($i = 1; $i -le $maxAttempts; $i++) {
    if (Test-Health $url) {
        $elapsed = (Get-Date) - $startTime
        Write-Host "`nService is healthy after $i attempt(s)."
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $elapsed)
        exit 0
    }

    Write-Host "[$i/$maxAttempts] Not ready. Retrying in $waitSeconds second(s)..."
    Start-Sleep -Seconds $waitSeconds
}

# ── FAILURE ───────────────────────────────────────────────────────────
Write-Error "`nService did not become healthy in time: $url"
exit 1
