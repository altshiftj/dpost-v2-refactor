<# ========================= 05-run.ps1 =========================
Purpose:
- Unified application startup script for all access methods
- Handles service registration and application launching
- Supports local, direct SSH, and router tunnel execution
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    [switch] $Diagnostics
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"
. "$PSScriptRoot\deploy-helpers.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up run environment"

Enable-PipelineDiagnostics -Enabled:$Diagnostics -ScriptName "05-run"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    if ($global:__PipelineDiagnosticsEnabled) {
        Write-Host "Tooling versions (for diagnostics):"
        try { & cmd /c "plink.exe -V" } catch {}
        Write-Host "PATH: $env:PATH"
    }
    
    $remotePath = $env:REMOTE_PATH
    $binaryName = "wd-$env:CI_JOB_NAME.exe"
    $remoteExePath = "$remotePath\$binaryName"
    $taskName = "IPAT-Watchdog-$env:CI_JOB_NAME"
    
    Write-Host "Run Configuration:"
    Write-Host "  Target: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "  Executable: $remoteExePath"
    Write-Host "  Access Method: $($config.Method)"
    
    Write-PipelineStep "SERVICE SETUP" "Configuring Windows service/task"
    
    # Determine the user context to run under (prefer explicit RUN_AS_USER, else TARGET_USER, else current user)
    $taskRunUser = if ($env:RUN_AS_USER) { $env:RUN_AS_USER } elseif ($env:TARGET_USER) { $env:TARGET_USER } else { $env:USERNAME }
    Write-Host "Configured to run task as user: $taskRunUser"

    # Build path to the remote registration script copied during deploy
    $remoteRegisterScript = "$remotePath\register_task.ps1"

    # Execute based on access method
    switch ($config.Method) {
        "local" {
            Write-Host "Running locally..."
            
            # Execute registration locally via the standard script
            & $remoteRegisterScript -TaskName $taskName -ExePath $remoteExePath
            
            if ($LASTEXITCODE -ne 0) {
                Write-PipelineError "SERVICE SETUP" "Failed to register local service" $LASTEXITCODE
            }
        }
        
        "direct" {
            Write-Host "Running via direct SSH..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "SERVICE SETUP" "plink not found. Install PuTTY tools." 1
            }
            
            $sshConfig = @{
                Host = $env:TARGET_IP
                Port = $env:SSH_PORT
                User = $env:TARGET_USER
                Password = $env:TARGET_PASS
                HostKey = $env:SSH_HOSTKEY
            }
            
            # Test connection
            if (-not (Test-SSHConnection -Config $sshConfig)) {
                Write-PipelineError "SERVICE SETUP" "SSH connection test failed" 1
            }
            
            # Execute task registration via SSH using the remote register_task.ps1 (no EncodedCommand)
            $plinkArgs = New-PlinkBaseArgs -Config $sshConfig -LogPrefix 'plink-cmd'
            $plinkArgs += ("{0}@{1}" -f $sshConfig.User, $sshConfig.Host)
            $remoteCmdParts = @('powershell','-NoProfile','-ExecutionPolicy','Bypass','-File', $remoteRegisterScript, '-TaskName', ('"' + $taskName + '"'), '-ExePath', ('"' + $remoteExePath + '"'))
            $remoteCmd = ($remoteCmdParts -join ' ')
            $plinkArgs += $remoteCmd

            if ($global:__PipelineDiagnosticsEnabled) { Write-Host ("plink.exe {0}" -f (Write-MaskedArgs -InputArgs $plinkArgs)) }
            & cmd /c "plink.exe $($plinkArgs -join ' ')"
            $exitCode = $LASTEXITCODE
            
            if ($exitCode -ne 0) {
                Write-PipelineError "SERVICE SETUP" "Failed to register remote service via SSH" $exitCode
            }
        }
        
        "router" {
            Write-Host "Running via router tunnel..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "SERVICE SETUP" "plink not found. Install PuTTY tools." 1
            }
            
            $routerConfig = @{
                Host = $env:ROUTER_IP
                User = $env:ROUTER_USER
                KeyFile = $env:ROUTER_SSH_KEY
                HostKey = $env:ROUTER_SSH_HOSTKEY
                Password = $env:ROUTER_PASS
            }
            
            $targetConfig = @{
                Host = $env:TARGET_IP
                User = $env:TARGET_USER
                KeyFile = $env:TARGET_SSH_KEY
                HostKey = $env:TARGET_SSH_HOSTKEY
                Password = $env:TARGET_PASS
                TunnelPort = $env:TARGET_TUNNEL_PORT
            }
            
            # Test router connection
            if (-not (Test-SSHConnection -Config $routerConfig)) {
                Write-PipelineError "SERVICE SETUP" "Router SSH connection test failed" 1
            }
            
            # Start tunnel
            Write-Host "Starting SSH tunnel..."
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
                    Password = $targetConfig.Password
                }
                
                if (-not (Test-SSHConnection -Config $tunnelSSHConfig)) {
                    Write-PipelineError "SERVICE SETUP" "Target SSH connection through tunnel failed" 1
                }
                
                # Execute task registration through tunnel using the remote register_task.ps1 (no EncodedCommand)
                $plinkArgs = New-PlinkBaseArgs -Config $tunnelSSHConfig -LogPrefix 'plink-cmd'
                $plinkArgs += ("{0}@{1}" -f $tunnelSSHConfig.User, $tunnelSSHConfig.Host)
                $remoteCmdParts = @('powershell','-NoProfile','-ExecutionPolicy','Bypass','-File', $remoteRegisterScript, '-TaskName', ('"' + $taskName + '"'), '-ExePath', ('"' + $remoteExePath + '"'))
                $remoteCmd = ($remoteCmdParts -join ' ')
                $plinkArgs += $remoteCmd

                if ($global:__PipelineDiagnosticsEnabled) { Write-Host ("plink.exe {0}" -f (Write-MaskedArgs -InputArgs $plinkArgs)) }
                & cmd /c "plink.exe $($plinkArgs -join ' ')"
                $exitCode = $LASTEXITCODE
                
                if ($exitCode -ne 0) {
                    Write-PipelineError "SERVICE SETUP" "Failed to register remote service via tunnel" $exitCode
                }
                
            } finally {
                # Clean up tunnel
                if ($tunnelProcess) {
                    Stop-SSHTunnel -TunnelProcess $tunnelProcess
                }
            }
        }
        
        default {
            Write-PipelineError "SERVICE SETUP" "Unknown access method: $($config.Method)" 1
        }
    }
    
    Write-PipelineStep "VERIFICATION" "Verifying user-level task startup"
    
    # Wait a moment for service to start
    Start-Sleep -Seconds 5
    
    # Verify service is running (basic check)
    switch ($config.Method) {
        "local" {
            $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($task -and $task.State -eq 'Running') {
                Write-Host "Task is running locally under user context." -ForegroundColor Green
            } else {
                Write-Warning "Task registered under user context but not running yet. If no session is active, it will start at next logon of $taskRunUser. Check Task Scheduler -> Task Scheduler Library for '$taskName'."
            }
        }
        
        default {
            Write-Host "Task registered remotely under user context. If it didn't start, it will launch at that user's next logon. Use the health check script or Task Scheduler on the target to verify." -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "Verbose error details:" -ForegroundColor Red
    $_ | Format-List * | Out-String | Write-Host
    if ($_.InvocationInfo) { Write-Host "At: $($_.InvocationInfo.PositionMessage)" }
    Write-DiagnosticSnapshot -Title "Run Failure Snapshot"
    Write-PipelineError "RUN" "Run failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nRun pipeline completed successfully." -ForegroundColor Green
