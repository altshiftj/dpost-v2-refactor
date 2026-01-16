<#
    Simulate GitLab "health" stage by polling a /health endpoint
    Uses SSH tunnel to reach internal target via port 22
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# ── CONFIG ────────────────────────────────────────────────────────────
$targetIP     = $env:TARGET_IP
$targetUser   = $env:TARGET_USER
$targetPass   = $env:TARGET_PASS
$targetKey    = $env:TARGET_SSH_KEY
$sshPort      = $env:SSH_PORT
$sshHostKey   = $env:SSH_HOSTKEY
$remotePort   = 8001
$localPort    = $env:TUN_PORT_1
$healthPath   = "/health"
$maxAttempts  = 30
$waitSeconds  = 5

if (-not (Get-Command plink.exe -ErrorAction SilentlyContinue)) {
    Write-Error "plink.exe not found in PATH."
    exit 1
}

# ── SSH TUNNEL ────────────────────────────────────────────────────────
Write-Host "Opening SSH tunnel to ${targetIP}:$remotePort -> 127.0.0.1:$localPort..."

$tunnelArgs = @(
    "-batch", "-N", "-L", "${localPort}:127.0.0.1:$remotePort",
    "-P", $sshPort
)
$tunnelArgs += Get-SSHAuthArgs -KeyPath $targetKey -HostKey $sshHostKey -Password $targetPass
$tunnelArgs += "$targetUser@$targetIP"

# Launch tunnel as background process
$tunnelProc = Start-Process -FilePath plink.exe -ArgumentList $tunnelArgs -NoNewWindow -PassThru

# ── HEALTH LOOP ───────────────────────────────────────────────────────
$url = "http://127.0.0.1:$localPort$healthPath"
$startTime = Get-Date
Write-Host "Waiting for service at $url ..."

function Test-Health {
    param ([string]$uri)

    try {
        $null = Invoke-RestMethod -Uri $uri -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

for ($i = 1; $i -le $maxAttempts; $i++) {
    if (Test-Health $url) {
        $elapsed = (Get-Date) - $startTime
        Write-Host "`nService is healthy after $i attempt(s)."
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $elapsed)

        Stop-Process -Id $tunnelProc.Id -Force
        exit 0
    }

    Write-Host "[$i/$maxAttempts] Not ready. Retrying in $waitSeconds second(s)..."
    Start-Sleep -Seconds $waitSeconds
}

# ── CLEANUP + FAILURE ─────────────────────────────────────────────────
Write-Error "`nService did not become healthy in time: $url"
Stop-Process -Id $tunnelProc.Id -Force
exit 1
