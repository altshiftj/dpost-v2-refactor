<# ========================= 06-health_check.ps1 =========================
Purpose:
- Unified health check script for all access methods
- Verifies application is running and responding
- Checks service status, file system, and application endpoints
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    
    [Parameter(Mandatory = $false)]
    [int] $TimeoutSeconds = 30
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"
. "$PSScriptRoot\deploy-helpers.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up health check environment"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    $remotePath = $env:REMOTE_PATH
    $binaryName = "wd-$env:CI_JOB_NAME.exe"
    $remoteExePath = "$remotePath\$binaryName"
    
    Write-Host "Health Check Configuration:"
    Write-Host "  Target: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "  Executable: $remoteExePath"
    Write-Host "  Access Method: $($config.Method)"
    Write-Host "  Timeout: $TimeoutSeconds seconds"
    
    # Health check script to run on target
    $healthCheckScript = @"
`$results = @{}
`$exePath = '$remoteExePath'
`$taskName = 'IPAT-Watchdog'

# Check 1: File exists
`$results.FileExists = Test-Path `$exePath
Write-Host "File exists: `$(`$results.FileExists)"

# Check 2: Scheduled task status
try {
    `$task = Get-ScheduledTask -TaskName `$taskName -ErrorAction SilentlyContinue
    `$results.TaskExists = `$task -ne `$null
    `$results.TaskState = if (`$task) { `$task.State } else { 'NotFound' }
    Write-Host "Task exists: `$(`$results.TaskExists)"
    Write-Host "Task state: `$(`$results.TaskState)"
} catch {
    `$results.TaskExists = `$false
    `$results.TaskState = 'Error'
    Write-Host "Task check failed: `$(`$_.Exception.Message)"
}

# Check 3: Process running
try {
    `$processes = Get-Process | Where-Object { `$_.Path -eq `$exePath }
    `$results.ProcessRunning = `$processes.Count -gt 0
    `$results.ProcessCount = `$processes.Count
    if (`$processes) {
        `$results.ProcessId = `$processes[0].Id
        `$results.ProcessStartTime = `$processes[0].StartTime
    }
    Write-Host "Process running: `$(`$results.ProcessRunning)"
    Write-Host "Process count: `$(`$results.ProcessCount)"
} catch {
    `$results.ProcessRunning = `$false
    `$results.ProcessCount = 0
    Write-Host "Process check failed: `$(`$_.Exception.Message)"
}

# Check 4: Application logs (if available)
`$logPath = Join-Path '$remotePath' 'logs'
if (Test-Path `$logPath) {
    try {
        `$recentLogs = Get-ChildItem `$logPath -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 3
        `$results.RecentLogFiles = `$recentLogs.Count
        if (`$recentLogs) {
            `$results.LatestLogFile = `$recentLogs[0].Name
            `$results.LatestLogTime = `$recentLogs[0].LastWriteTime
        }
        Write-Host "Recent log files: `$(`$results.RecentLogFiles)"
    } catch {
        Write-Host "Log check failed: `$(`$_.Exception.Message)"
    }
}

# Check 5: HTTP endpoints (if applicable)
`$httpPorts = @(8000, 8001)
foreach (`$port in `$httpPorts) {
    try {
        `$response = Invoke-WebRequest -Uri "http://localhost:`$port/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        `$results["Http`$port"] = `$response.StatusCode -eq 200
        Write-Host "HTTP `$port health: `$(`$results["Http`$port"])"
    } catch {
        `$results["Http`$port"] = `$false
        Write-Host "HTTP `$port health: False (connection failed)"
    }
}

# Check 6: Version information
try {
    `$versionPath = Join-Path '$remotePath' 'version.txt'
    if (Test-Path `$versionPath) {
        `$versionContent = Get-Content `$versionPath
        Write-Host "Version file contents:"
        `$versionContent | ForEach-Object { Write-Host "  `$_" }
        `$results.VersionFileExists = `$true
    } else {
        `$results.VersionFileExists = `$false
        Write-Host "Version file not found"
    }
} catch {
    Write-Host "Version check failed: `$(`$_.Exception.Message)"
}

# Overall health assessment
`$healthy = `$results.FileExists -and `$results.TaskExists -and (`$results.TaskState -eq 'Running') -and `$results.ProcessRunning
Write-Host "`nOverall Health: `$(if (`$healthy) { 'HEALTHY' } else { 'UNHEALTHY' })"

exit $(if (`$healthy) { 0 } else { 1 })
"@

    Write-PipelineStep "HEALTH CHECK" "Performing application health check"
    
    $healthCheckSuccess = $false
    $healthCheckOutput = ""
    
    # Execute health check based on access method
    switch ($config.Method) {
        "local" {
            Write-Host "Performing local health check..."
            
            try {
                $healthCheckOutput = Invoke-Expression $healthCheckScript
                $healthCheckSuccess = $LASTEXITCODE -eq 0
            } catch {
                Write-Warning "Local health check failed: $($_.Exception.Message)"
                $healthCheckSuccess = $false
            }
        }
        
        "direct" {
            Write-Host "Performing health check via direct SSH..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "HEALTH CHECK" "plink not found. Install PuTTY tools." 1
            }
            
            $sshConfig = @{
                Host = $env:TARGET_IP
                Port = $env:SSH_PORT
                User = $env:TARGET_USER
                HostKey = $env:SSH_HOSTKEY
            }
            
            # Test connection
            if (-not (Test-SSHConnection -Config $sshConfig)) {
                Write-PipelineError "HEALTH CHECK" "SSH connection test failed" 1
            }
            
            # Execute health check via SSH
            $exitCode = Invoke-SSHCommand -Config $sshConfig -Command $healthCheckScript
            $healthCheckSuccess = $exitCode -eq 0
        }
        
        "router" {
            Write-Host "Performing health check via router tunnel..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "HEALTH CHECK" "plink not found. Install PuTTY tools." 1
            }
            
            $routerConfig = @{
                Host = $env:ROUTER_IP
                User = $env:ROUTER_USER
                KeyFile = $env:ROUTER_SSH_KEY
                HostKey = $env:ROUTER_SSH_HOSTKEY
            }
            
            $targetConfig = @{
                Host = $env:TARGET_IP
                User = $env:TARGET_USER
                KeyFile = $env:TARGET_SSH_KEY
                HostKey = $env:TARGET_SSH_HOSTKEY
                TunnelPort = $env:TARGET_TUNNEL_PORT
            }
            
            # Test router connection
            if (-not (Test-SSHConnection -Config $routerConfig)) {
                Write-PipelineError "HEALTH CHECK" "Router SSH connection test failed" 1
            }
            
            # Start tunnel
            Write-Host "Starting SSH tunnel for health check..."
            $tunnelProcess = Start-SSHTunnel -RouterConfig $routerConfig -TargetConfig $targetConfig
            
            try {
                # Wait for tunnel to establish
                Start-Sleep -Seconds 3
                
                # Test target connection through tunnel
                $tunnelSSHConfig = @{
                    Host = "127.0.0.1"
                    Port = $targetConfig.TunnelPort
                    User = $targetConfig.User
                    KeyFile = $targetConfig.KeyFile
                    HostKey = $targetConfig.HostKey
                }
                
                if (-not (Test-SSHConnection -Config $tunnelSSHConfig)) {
                    Write-PipelineError "HEALTH CHECK" "Target SSH connection through tunnel failed" 1
                }
                
                # Execute health check through tunnel
                $exitCode = Invoke-SSHCommand -Config $tunnelSSHConfig -Command $healthCheckScript
                $healthCheckSuccess = $exitCode -eq 0
                
            } finally {
                # Clean up tunnel
                if ($tunnelProcess) {
                    Stop-SSHTunnel -TunnelProcess $tunnelProcess
                }
            }
        }
        
        default {
            Write-PipelineError "HEALTH CHECK" "Unknown access method: $($config.Method)" 1
        }
    }
    
    Write-PipelineStep "RESULTS" "Health check results"
    
    if ($healthCheckSuccess) {
        Write-Host "`nHealth check PASSED - Application is healthy" -ForegroundColor Green
    } else {
        Write-Host "`nHealth check FAILED - Application may have issues" -ForegroundColor Red
        
        # For troubleshooting, suggest next steps
        Write-Host "`nTroubleshooting suggestions:" -ForegroundColor Yellow
        Write-Host "  1. Check if the application was deployed correctly"
        Write-Host "  2. Verify the scheduled task is configured properly"
        Write-Host "  3. Check application logs for errors"
        Write-Host "  4. Ensure all required dependencies are installed"
        Write-Host "  5. Verify network connectivity and firewall settings"
        
        exit 1
    }
    
} catch {
    Write-PipelineError "HEALTH CHECK" "Health check failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
}

Write-Host "`nHealth check pipeline completed successfully." -ForegroundColor Green
