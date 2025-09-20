<# ========================= 06-health_check.ps1 =========================
Purpose:
- Consolidated health check using SSH tunnel + local HTTP polling
- Supports direct SSH and router tunnel access methods
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    [Parameter(Mandatory = $false)]
    [int] $TimeoutSeconds = 30,
    [switch] $Diagnostics
)

# Load utilities
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"
. "$PSScriptRoot\deploy-helpers.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up health check environment"

Enable-PipelineDiagnostics -Enabled:$Diagnostics -ScriptName "06-health_check"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT

    if ($global:__PipelineDiagnosticsEnabled) {
        Write-Host "Tooling versions (for diagnostics):"
        try { & cmd /c "plink.exe -V" } catch {}
        Write-Host "PATH: $env:PATH"
    }

    # Determine SSH endpoint (direct vs router)
    $method = $config.Method.ToLower()
    $remotePort = 8001
    $localPort = if ($env:TARGET_TUNNEL_PORT) { $env:TARGET_TUNNEL_PORT } elseif ($env:TUN_PORT_1) { $env:TUN_PORT_1 } else { 18001 }

    if (-not (Get-Command plink.exe -ErrorAction SilentlyContinue)) {
        Write-PipelineError "VALIDATION" "plink.exe not found in PATH." 1
    }

    $sshLoginHost = $null
    $sshLoginUser = $null
    $sshPassword  = $null
    $sshHostKey   = $null
    $sshPort      = 22
    $forwardHost  = '127.0.0.1'

    switch ($method) {
        'router' {
            $sshLoginHost = $env:ROUTER_IP
            $sshLoginUser = $env:ROUTER_USER
            $sshPassword  = $env:ROUTER_PASS
            $sshHostKey   = $env:ROUTER_SSH_HOSTKEY
            $sshPort      = if ($env:SSH_PORT) { [int]$env:SSH_PORT } else { 22 }
            # When connecting to router, forward to target IP on remote side
            $forwardHost  = $env:TARGET_IP
        }
        default {
            $sshLoginHost = $env:TARGET_IP
            $sshLoginUser = $env:TARGET_USER
            $sshPassword  = $env:TARGET_PASS
            $sshHostKey   = $env:SSH_HOSTKEY
            $sshPort      = if ($env:SSH_PORT) { [int]$env:SSH_PORT } else { 22 }
            $forwardHost  = '127.0.0.1'
        }
    }

    Write-Host "Health Check Configuration:"
    Write-Host "  Access Method: $method"
    Write-Host ("  SSH Login: {0}@{1}:{2}" -f $sshLoginUser, $sshLoginHost, $sshPort)
    Write-Host ("  Tunnel: {0} -> {1}:{2}" -f $localPort, $forwardHost, $remotePort)
    Write-Host "  Timeout: $TimeoutSeconds seconds"

    Write-PipelineStep "HEALTH CHECK" "Opening SSH tunnel and polling /health"

    # Build plink tunnel args (options-first)
    $tunnelArgs = @('-batch','-N','-L',("{0}:{1}:{2}" -f $localPort, $forwardHost, $remotePort))
    if ($sshPort -and $sshPort -ne 22) { $tunnelArgs += '-P'; $tunnelArgs += $sshPort }
    if ($sshPassword) { $tunnelArgs += '-pw'; $tunnelArgs += $sshPassword }
    if ($sshHostKey) { $tunnelArgs += '-hostkey'; $tunnelArgs += $sshHostKey }
    if ($global:__PipelineDiagnosticsEnabled) {
        $logDir = if ($env:PROJECT_ROOT) { Join-Path $env:PROJECT_ROOT 'build\logs' } else { Join-Path $PSScriptRoot 'logs' }
        if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        $sshLogPath = Join-Path $logDir ("plink-tunnel-{0}-{1:yyyyMMdd-HHmmss}.log" -f $sshLoginHost,(Get-Date))
        $tunnelArgs += '-sshlog'; $tunnelArgs += $sshLogPath
        Write-Host ("plink.exe {0} {1}@{2}" -f (Write-MaskedArgs -InputArgs $tunnelArgs), $sshLoginUser, $sshLoginHost)
    }
    $tunnelArgs += ("{0}@{1}" -f $sshLoginUser, $sshLoginHost)

    # Start tunnel
    $tunnelProc = Start-Process -FilePath plink.exe -ArgumentList $tunnelArgs -NoNewWindow -PassThru

    # Poll the health endpoint via the tunnel
    $url = "http://127.0.0.1:$localPort/health"
    $startTime = Get-Date
    $deadline = $startTime.AddSeconds($TimeoutSeconds)
    Write-Host "Waiting for service at $url ..."

    $healthCheckSuccess = $false
    $attempt = 0
    while ((Get-Date) -lt $deadline) {
        $attempt++
        try {
            $null = Invoke-RestMethod -Uri $url -TimeoutSec 3 -ErrorAction Stop
            $healthCheckSuccess = $true
            break
        } catch {
            if ($tunnelProc.HasExited) {
                Write-Warning "SSH tunnel process exited prematurely (exit code: $($tunnelProc.ExitCode))."
                break
            }
            Start-Sleep -Seconds 3
        }
    }

    # Cleanup tunnel
    if ($tunnelProc -and (-not $tunnelProc.HasExited)) {
        try { Stop-Process -Id $tunnelProc.Id -Force } catch {}
    }

    Write-PipelineStep "RESULTS" "Health check results"
    if ($healthCheckSuccess) {
        $elapsed = (Get-Date) - $startTime
        Write-Host "Health check PASSED after $attempt attempt(s)." -ForegroundColor Green
        Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $elapsed)
    } else {
        Write-Host "Health check FAILED - Application may have issues" -ForegroundColor Red
        Write-Host "Troubleshooting suggestions:" -ForegroundColor Yellow
        Write-Host "  1. Check if the application was deployed correctly"
        Write-Host "  2. Verify the scheduled task is configured properly"
        Write-Host "  3. Check application logs for errors"
        Write-Host "  4. Ensure all required dependencies are installed"
        Write-Host "  5. Verify network connectivity and firewall settings"
        exit 1
    }

} catch {
    Write-Host "Verbose error details:" -ForegroundColor Red
    $_ | Format-List * | Out-String | Write-Host
    if ($_.InvocationInfo) { Write-Host "At: $($_.InvocationInfo.PositionMessage)" }
    Write-DiagnosticSnapshot -Title "Health Check Failure Snapshot"
    Write-PipelineError "HEALTH CHECK" "Health check failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nHealth check pipeline completed successfully." -ForegroundColor Green

