. "$PSScriptRoot\env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

# simulate_health.ps1
# Simulate your GitLab "health" stage locally in PowerShell

# --- SETTINGS ---
$targetIP = "127.0.0.1"
$healthPort = 8001
$healthPath = "/health"
$maxAttempts = 30
$waitSeconds = 2

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Define Health Check Function ---
function Test-Health {
    param (
        [string]$url
    )

    try {
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

# --- Step 2: Start Health Checking ---
$url = "http://$targetIP`:$healthPort$healthPath"
Write-Host "Waiting for service at $url ..."

for ($i = 0; $i -lt $maxAttempts; $i++) {
    if (Test-Health -url $url) {
        Write-Host "Service is healthy!"
        $endTime = Get-Date
        $duration = $endTime - $startTime
        Write-Host ("Health check complete. Elapsed time: {0:hh\:mm\:ss}" -f $duration)
        exit 0
    }

    Write-Host "Health check attempt $($i + 1) failed. Retrying in $waitSeconds second(s)..."
    Start-Sleep -Seconds $waitSeconds
}

Write-Error "Service did not become healthy in time!"
exit 1
