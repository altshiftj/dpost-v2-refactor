<#
    Health check via SSH tunnel through router
    - Create SSH tunnel from local machine -> router -> Windows PC
    - Poll health endpoint through tunnel
#>

# ── ENV + LOCATION ────────────────────────────────────────────────────
. "$PSScriptRoot\00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

# ── CONFIG ────────────────────────────────────────────────────────────
$routerIP    = $env:ROUTER_IP
$routerPort  = $env:ROUTER_PORT
$routerUser  = $env:ROUTER_USER
$routerKey   = $env:ROUTER_SSH_KEY
$routerHK    = $env:ROUTER_SSH_HOSTKEY

$targetIP    = $env:TARGET_IP
$remotePort  = 8001
$localPort   = $env:TUN_PORT_1
if (-not $localPort) { $localPort = 18001 }   # default local port if none provided

$healthPath  = "/health"
$maxAttempts = 30
$waitSeconds = 5

if (!(Get-Command plink.exe -ErrorAction SilentlyContinue)) {
    Write-Error "plink.exe not found in PATH."
    exit 1
}

Write-Host "=== Health Check via Router Tunnel ==="
Write-Host ("Router: {0}" -f $routerIP)
Write-Host ("Target: {0}" -f $targetIP)
Write-Host ("Tunnel: localhost:{0} -> {1}:{2}" -f $localPort, $targetIP, $remotePort)

# ── SSH TUNNEL THROUGH ROUTER ────────────────────────────────────────
Write-Host ""
Write-Host "Setting up SSH tunnel through router..."
Write-Host ("Local Port: {0} -> Router: {1} -> Target: {2}:{3}" -f $localPort, $routerIP, $targetIP, $remotePort)

# Build plink args for: localhost:$localPort -> router -> $targetIP:$remotePort
$plinkArgs = @(
    "-batch","-N",
    "-L",("{0}:{1}:{2}" -f $localPort, $targetIP, $remotePort),
    "-P",$routerPort,
    "-i",$routerKey,
    "-hostkey",$routerHK,
    ("{0}@{1}" -f $routerUser, $routerIP)
)

Write-Host ("Tunnel command: plink.exe {0}" -f ($plinkArgs -join ' '))

# Launch tunnel as background process
$tunnelProc = Start-Process -FilePath plink.exe -ArgumentList $plinkArgs -NoNewWindow -PassThru
Write-Host ("SSH tunnel process started (PID: {0})" -f $tunnelProc.Id)

# Give tunnel time to establish
Start-Sleep -Seconds 3

# ── TUNNEL TCP SANITY CHECK ──────────────────────────────────────────
$tnc = $null
try {
    $tnc = Test-NetConnection -ComputerName 127.0.0.1 -Port $localPort -WarningAction SilentlyContinue
} catch {}
if (-not ($tnc -and $tnc.TcpTestSucceeded)) {
    Write-Error ("Tunnel TCP test failed: cannot reach 127.0.0.1:{0}" -f $localPort)
    try {
        if ($tunnelProc -and -not $tunnelProc.HasExited) { Stop-Process -Id $tunnelProc.Id -Force }
    } catch {}
    exit 1
}

# ── HEALTH CHECK LOOP ─────────────────────────────────────────────────
$url = ("http://127.0.0.1:{0}{1}" -f $localPort, $healthPath)
$startTime = Get-Date
Write-Host ""
Write-Host ("Checking service health at: {0}" -f $url)

function Test-Health {
    param ([string]$uri)
    try {
        $response = Invoke-RestMethod -Uri $uri -TimeoutSec 5 -ErrorAction Stop
        Write-Host ("Health response: {0}" -f ($response | ConvertTo-Json -Compress))
        return $true
    } catch {
        Write-Host ("Health check failed: {0}" -f $_.Exception.Message)
        return $false
    }
}

$healthOK = $false
for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host ("[{0}/{1}] Checking health..." -f $i, $maxAttempts)

    if (Test-Health $url) {
        $elapsed = (Get-Date) - $startTime
        Write-Host ""
        Write-Host ("Service is healthy after {0} attempt(s)!" -f $i)
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $elapsed)
        $healthOK = $true
        break
    }

    if ($i -lt $maxAttempts) {
        Write-Host ("Retrying in {0} second(s)..." -f $waitSeconds)
        Start-Sleep -Seconds $waitSeconds
    }
}

# ── CLEANUP TUNNEL ────────────────────────────────────────────────────
Write-Host ""
Write-Host "Cleaning up SSH tunnel..."
try {
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        Stop-Process -Id $tunnelProc.Id -Force
        Write-Host "SSH tunnel terminated"
    }
} catch {
    Write-Warning ("Failed to clean up tunnel process: {0}" -f $_)
}

# ── FINAL RESULT ──────────────────────────────────────────────────────
if ($healthOK) {
    Write-Host ""
    Write-Host "=== Health Check PASSED ==="
    exit 0
} else {
    Write-Error ""
    Write-Error "=== Health Check FAILED ==="
    Write-Error ("Service did not respond to health checks at: {0}" -f $url)
    exit 1
}
