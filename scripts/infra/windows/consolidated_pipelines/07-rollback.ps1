<# ========================= 07-rollback.ps1 =========================
Purpose:
- Unified rollback script for all access methods
- Restores previous version of application and services
- Handles rollback for local, direct SSH, and router tunnel configurations
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    
    [Parameter(Mandatory = $false)]
    [switch] $Force
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"
. "$PSScriptRoot\deploy-helpers.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up rollback environment"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    $remotePath = $env:REMOTE_PATH
    $binaryName = "wd-$env:CI_JOB_NAME.exe"
    $remoteExePath = "$remotePath\$binaryName"
    $backupBinaryName = $binaryName -replace '\.exe$', '_backup.exe'
    $backupVersionName = 'version_backup.txt'
    
    Write-Host "Rollback Configuration:"
    Write-Host "  Target: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "  Current: $remoteExePath"
    Write-Host "  Backup: $remotePath\$backupBinaryName"
    Write-Host "  Access Method: $($config.Method)"
    Write-Host "  Force: $Force"
    
    # Rollback script to run on target
    $rollbackScript = @"
`$remotePath = '$remotePath'
`$binaryName = '$binaryName'
`$backupBinaryName = '$backupBinaryName'
`$backupVersionName = '$backupVersionName'
`$taskName = 'IPAT-Watchdog'
`$force = `$$Force

`$currentExe = Join-Path `$remotePath `$binaryName
`$backupExe = Join-Path `$remotePath `$backupBinaryName
`$currentVersion = Join-Path `$remotePath 'version.txt'
`$backupVersion = Join-Path `$remotePath `$backupVersionName

Write-Host "Starting rollback process..."

# Check if backup files exist
if (-not (Test-Path `$backupExe)) {
    Write-Error "Backup executable not found: `$backupExe"
    exit 1
}

if (-not `$force) {
    Write-Host "Backup files found:"
    Write-Host "  Executable: `$backupExe"
    if (Test-Path `$backupVersion) {
        Write-Host "  Version file: `$backupVersion"
        Write-Host "  Backup version content:"
        Get-Content `$backupVersion | ForEach-Object { Write-Host "    `$_" }
    }
    
    Write-Host "`nCurrent version content (if available):"
    if (Test-Path `$currentVersion) {
        Get-Content `$currentVersion | ForEach-Object { Write-Host "    `$_" }
    } else {
        Write-Host "    No current version file found"
    }
    
    `$confirmation = Read-Host "`nProceed with rollback? (y/N)"
    if (`$confirmation -notmatch '^[Yy]') {
        Write-Host "Rollback cancelled by user"
        exit 0
    }
}

Write-Host "`nStopping current application..."

# Stop the scheduled task
try {
    Stop-ScheduledTask -TaskName `$taskName -ErrorAction SilentlyContinue
    Write-Host "Stopped scheduled task: `$taskName"
} catch {
    Write-Warning "Failed to stop scheduled task: `$(`$_.Exception.Message)"
}

# Stop any running processes
try {
    Get-Process | Where-Object { `$_.Path -eq `$currentExe } | Stop-Process -Force
    Write-Host "Stopped running processes"
} catch {
    Write-Warning "Failed to stop processes: `$(`$_.Exception.Message)"
}

# Wait for processes to fully stop
Start-Sleep -Seconds 3

Write-Host "`nPerforming rollback..."

# Backup current files (in case we need to roll forward)
if (Test-Path `$currentExe) {
    `$rollforwardExe = `$currentExe -replace '\.exe`$', '_rollforward.exe'
    try {
        Copy-Item `$currentExe `$rollforwardExe -Force
        Write-Host "Created roll-forward backup: `$rollforwardExe"
    } catch {
        Write-Warning "Failed to create roll-forward backup: `$(`$_.Exception.Message)"
    }
}

if (Test-Path `$currentVersion) {
    `$rollforwardVersion = Join-Path `$remotePath 'version_rollforward.txt'
    try {
        Copy-Item `$currentVersion `$rollforwardVersion -Force
        Write-Host "Created roll-forward version backup: `$rollforwardVersion"
    } catch {
        Write-Warning "Failed to create roll-forward version backup: `$(`$_.Exception.Message)"
    }
}

# Restore backup files
try {
    Copy-Item `$backupExe `$currentExe -Force
    Write-Host "Restored executable from backup"
} catch {
    Write-Error "Failed to restore executable: `$(`$_.Exception.Message)"
    exit 1
}

if (Test-Path `$backupVersion) {
    try {
        Copy-Item `$backupVersion `$currentVersion -Force
        Write-Host "Restored version file from backup"
    } catch {
        Write-Warning "Failed to restore version file: `$(`$_.Exception.Message)"
    }
}

Write-Host "`nRestarting application..."

# Start the scheduled task
try {
    Start-ScheduledTask -TaskName `$taskName
    Write-Host "Started scheduled task: `$taskName"
} catch {
    Write-Error "Failed to start scheduled task: `$(`$_.Exception.Message)"
    exit 1
}

# Wait for application to start
Start-Sleep -Seconds 5

# Verify the application is running
`$isRunning = `$false
try {
    `$processes = Get-Process | Where-Object { `$_.Path -eq `$currentExe }
    `$isRunning = `$processes.Count -gt 0
    if (`$isRunning) {
        Write-Host "Application is running (PID: `$(`$processes[0].Id))"
    }
} catch {
    Write-Warning "Failed to verify application status: `$(`$_.Exception.Message)"
}

if (`$isRunning) {
    Write-Host "`nRollback completed successfully" -ForegroundColor Green
    Write-Host "Application has been restored to the previous version"
} else {
    Write-Warning "`nRollback completed but application may not be running properly"
    Write-Host "Check the application manually or run a health check"
}

exit $(if (`$isRunning) { 0 } else { 1 })
"@

    Write-PipelineStep "ROLLBACK" "Performing application rollback"
    
    $rollbackSuccess = $false
    
    # Execute rollback based on access method
    switch ($config.Method) {
        "local" {
            Write-Host "Performing local rollback..."
            
            try {
                $rollbackOutput = Invoke-Expression $rollbackScript
                $rollbackSuccess = $LASTEXITCODE -eq 0
            } catch {
                Write-Warning "Local rollback failed: $($_.Exception.Message)"
                $rollbackSuccess = $false
            }
        }
        
        "direct" {
            Write-Host "Performing rollback via direct SSH..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "ROLLBACK" "plink not found. Install PuTTY tools." 1
            }
            
            $sshConfig = @{
                Host = $env:TARGET_IP
                Port = $env:SSH_PORT
                User = $env:TARGET_USER
                HostKey = $env:SSH_HOSTKEY
            }
            
            # Test connection
            if (-not (Test-SSHConnection -Config $sshConfig)) {
                Write-PipelineError "ROLLBACK" "SSH connection test failed" 1
            }
            
            # Execute rollback via SSH
            $exitCode = Invoke-SSHCommand -Config $sshConfig -Command $rollbackScript
            $rollbackSuccess = $exitCode -eq 0
        }
        
        "router" {
            Write-Host "Performing rollback via router tunnel..."
            
            # Check SSH tools
            if (-not (Get-Command plink -ErrorAction SilentlyContinue)) {
                Write-PipelineError "ROLLBACK" "plink not found. Install PuTTY tools." 1
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
                Write-PipelineError "ROLLBACK" "Router SSH connection test failed" 1
            }
            
            # Start tunnel
            Write-Host "Starting SSH tunnel for rollback..."
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
                    Write-PipelineError "ROLLBACK" "Target SSH connection through tunnel failed" 1
                }
                
                # Execute rollback through tunnel
                $exitCode = Invoke-SSHCommand -Config $tunnelSSHConfig -Command $rollbackScript
                $rollbackSuccess = $exitCode -eq 0
                
            } finally {
                # Clean up tunnel
                if ($tunnelProcess) {
                    Stop-SSHTunnel -TunnelProcess $tunnelProcess
                }
            }
        }
        
        default {
            Write-PipelineError "ROLLBACK" "Unknown access method: $($config.Method)" 1
        }
    }
    
    Write-PipelineStep "VERIFICATION" "Verifying rollback"
    
    if ($rollbackSuccess) {
        Write-Host "`nRollback completed successfully" -ForegroundColor Green
        Write-Host "Application has been restored to the previous version"
        Write-Host "`nRecommendations:" -ForegroundColor Yellow
        Write-Host "  1. Run a health check to verify the application is working"
        Write-Host "  2. Monitor application logs for any issues"
        Write-Host "  3. Test critical functionality"
        Write-Host "  4. Consider investigating why the rollback was necessary"
    } else {
        Write-Host "`nRollback may have failed or encountered issues" -ForegroundColor Red
        Write-Host "`nTroubleshooting suggestions:" -ForegroundColor Yellow
        Write-Host "  1. Check if backup files existed on the target system"
        Write-Host "  2. Verify manual rollback by connecting to the target system"
        Write-Host "  3. Check scheduled task configuration"
        Write-Host "  4. Ensure proper permissions for file operations"
        
        exit 1
    }
    
} catch {
    Write-PipelineError "ROLLBACK" "Rollback failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
}

Write-Host "`nRollback pipeline completed successfully." -ForegroundColor Green
