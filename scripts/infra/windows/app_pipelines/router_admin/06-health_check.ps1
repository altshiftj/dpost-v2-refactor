<#
    Health check via SSH tunnel through router
    - Create SSH tunnel from local machine -> router -> Windows PC
    - Poll health endpoint through tunnel
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# ── CONFIG ────────────────────────────────────────────────────────────
$routerIP     = $env:ROUTER_IP
$targetIP     = $env:TARGET_IP
$remotePort   = 8001
$localPort    = $env:TUN_PORT_1
$healthPath   = "/health"
$maxAttempts  = 30
$waitSeconds  = 5

if (-not (Get-Command plink.exe -ErrorAction SilentlyContinue)) {
    Write-Error "plink.exe not found in PATH."
    exit 1
}

Write-Host "=== Health Check via Router Tunnel ==="
Write-Host "Router: $routerIP"
Write-Host "Target: $targetIP"
Write-Host "Tunnel: localhost:$localPort -> $targetIP`:$remotePort"

# ── SSH TUNNEL THROUGH ROUTER ────────────────────────────────────────
Write-Host "`nSetting up SSH tunnel through router..."
Write-Host "Local Port: $localPort -> Router: $routerIP -> Target: $targetIP`:$remotePort"

# Create tunnel: localhost:localPort -> router -> targetIP:remotePort
$tunnelArgs = Get-TunnelSSHCommand -LocalPort $localPort -RemoteHost $targetIP -RemotePort $remotePort

Write-Host "Tunnel command: plink.exe $($tunnelArgs -join ' ')"

# Launch tunnel as background process
$tunnelProc = Start-Process -FilePath plink.exe -ArgumentList $tunnelArgs -NoNewWindow -PassThru
Write-Host "SSH tunnel process started (PID: $($tunnelProc.Id))"

# Give tunnel time to establish
Start-Sleep -Seconds 3

# ── HEALTH CHECK LOOP ─────────────────────────────────────────────────
$url = "http://127.0.0.1:$localPort$healthPath"
$startTime = Get-Date
Write-Host "`nChecking service health at: $url"

function Test-Health {
    param ([string]$uri)

    try {
        $response = Invoke-RestMethod -Uri $uri -TimeoutSec 5 -ErrorAction Stop
        Write-Host "Health response: $($response | ConvertTo-Json -Compress)"
        return $true
    } catch {
        Write-Host "Health check failed: $($_.Exception.Message)"
        return $false
    }
}

$healthOK = $false
for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host "[$i/$maxAttempts] Checking health..."
    
    if (Test-Health $url) {
        $elapsed = (Get-Date) - $startTime
        Write-Host "`n✓ Service is healthy after $i attempt(s)!"
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $elapsed)
        $healthOK = $true
        break
    }

    if ($i -lt $maxAttempts) {
        Write-Host "Retrying in $waitSeconds second(s)..."
        Start-Sleep -Seconds $waitSeconds
    }
}

# ── CLEANUP TUNNEL ────────────────────────────────────────────────────
Write-Host "`nCleaning up SSH tunnel..."
try {
    if (!$tunnelProc.HasExited) {
        Stop-Process -Id $tunnelProc.Id -Force
        Write-Host "SSH tunnel terminated"
    }
} catch {
    Write-Warning "Failed to clean up tunnel process: $_"
}

# ── FINAL RESULT ──────────────────────────────────────────────────────
if ($healthOK) {
    Write-Host "`n=== Health Check PASSED ==="
    exit 0
} else {
    Write-Error "`n=== Health Check FAILED ==="
    Write-Error "Service did not respond to health checks at: $url"
    exit 1
}
