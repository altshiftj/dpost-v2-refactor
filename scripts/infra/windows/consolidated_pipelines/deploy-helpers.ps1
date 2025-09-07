<# ========================= deploy-helpers.ps1 =========================
Purpose:
- Deployment helpers for different access methods
- Handles local, direct SSH, and router tunnel deployments
- Common deployment logic with method-specific implementations
================================================================ #>

# ------------------------------
# Local Deployment
# ------------------------------
function Deploy-Local {
    param(
        [hashtable] $DeployConfig,
        [string[]] $FilesToDeploy,
        [string] $RemotePath
    )
    
    Write-Host "Deploying locally to: $RemotePath"
    
    # Create directory if it doesn't exist
    if (-not (Test-Path $RemotePath)) {
        New-Item $RemotePath -Force -ItemType Directory | Out-Null
    }
    
    # Stop any running instances
    try {
        Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
        $exePath = Join-Path $RemotePath $DeployConfig.BinaryName
        Get-Process | Where-Object { $_.Path -eq $exePath } | Stop-Process -Force
    } catch {
        Write-Warning "Failed to stop running instances: $($_.Exception.Message)"
    }
    
    # Backup existing files
    foreach ($file in $FilesToDeploy[0..1]) {  # Only backup binary and version.txt
        $targetPath = Join-Path $RemotePath $file
        if (Test-Path $targetPath) {
            $backupPath = $targetPath -replace '\.(\w+)$', '_backup.$1'
            if (Test-Path $backupPath) {
                Remove-Item $backupPath -Force
            }
            Rename-Item -Path $targetPath -NewName $backupPath -Force
            Write-Host "Backed up: $file -> $([System.IO.Path]::GetFileName($backupPath))"
        }
    }
    
    # Copy files
    foreach ($file in $FilesToDeploy) {
        $sourcePath = if ($file -eq $DeployConfig.BinaryName) { $DeployConfig.BinaryPath } else { $file }
        $targetPath = Join-Path $RemotePath $file
        
        Copy-Item $sourcePath $targetPath -Force
        Write-Host "Copied: $file"
    }
    
    return $true
}

# ------------------------------
# Direct SSH Deployment
# ------------------------------
function Deploy-DirectSSH {
    param(
        [hashtable] $DeployConfig,
        [string[]] $FilesToDeploy,
        [string] $RemotePath,
        [hashtable] $SSHConfig
    )
    
    Write-Host "Deploying via direct SSH to: $($SSHConfig.User)@$($SSHConfig.Host):$RemotePath"
    
    # Test SSH connectivity
    if (-not (Test-SSHConnection -Config $SSHConfig)) {
        throw "SSH connection test failed"
    }
    
    # Create remote directory
    $createDirCmd = "if (!(Test-Path '$RemotePath')) { New-Item '$RemotePath' -Force -ItemType Directory }"
    Invoke-SSHCommand -Config $SSHConfig -Command $createDirCmd
    
    # Stop remote services
    $stopCmd = @"
try {
    Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
    Get-Process | Where-Object { `$_.Name -eq 'wd-$($DeployConfig.JobName)' } | Stop-Process -Force
} catch { }
"@
    Invoke-SSHCommand -Config $SSHConfig -Command $stopCmd
    
    # Backup existing files on remote
    foreach ($file in $FilesToDeploy[0..1]) {
        $backupCmd = @"
`$targetPath = Join-Path '$RemotePath' '$file'
if (Test-Path `$targetPath) {
    `$backupPath = `$targetPath -replace '\.(\w+)`$', '_backup.`$1'
    if (Test-Path `$backupPath) { Remove-Item `$backupPath -Force }
    Rename-Item -Path `$targetPath -NewName `$backupPath -Force
}
"@
        Invoke-SSHCommand -Config $SSHConfig -Command $backupCmd
    }
    
    # Copy files using PSCP
    foreach ($file in $FilesToDeploy) {
        $sourcePath = if ($file -eq $DeployConfig.BinaryName) { $DeployConfig.BinaryPath } else { $file }
        $remoteFile = "$($SSHConfig.User)@$($SSHConfig.Host):$RemotePath/$file"
        
        if (Get-Command pscp -ErrorAction SilentlyContinue) {
            # Build pscp arguments for PowerShell 5 compatibility
            $pscpArgs = @()
            $pscpArgs += "-batch"
            $pscpArgs += "-scp"
            
            if ($SSHConfig.KeyFile -and (Test-Path $SSHConfig.KeyFile)) {
                $pscpArgs += "-i"
                $pscpArgs += $SSHConfig.KeyFile
            }
            
            if ($SSHConfig.HostKey) {
                $pscpArgs += "-hostkey"
                $pscpArgs += $SSHConfig.HostKey
            }
            
            if ($SSHConfig.Port -and $SSHConfig.Port -ne "22") {
                $pscpArgs += "-P"
                $pscpArgs += $SSHConfig.Port
            }
            
            $pscpArgs += $sourcePath
            $pscpArgs += $remoteFile
            
            & cmd /c "pscp.exe $($pscpArgs -join ' ')"
        } else {
            throw "pscp not available. Install PuTTY tools and ensure they are in PATH."
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to copy $file via SCP (exit code: $LASTEXITCODE)"
        }
        
        Write-Host "Copied: $file"
    }
    
    return $true
}

# ------------------------------
# Router Tunnel Deployment
# ------------------------------
function Deploy-RouterTunnel {
    param(
        [hashtable] $DeployConfig,
        [string[]] $FilesToDeploy,
        [string] $RemotePath,
        [hashtable] $RouterConfig,
        [hashtable] $TargetConfig
    )
    
    Write-Host "Deploying via router tunnel:"
    Write-Host "  Router: $($RouterConfig.User)@$($RouterConfig.Host)"
    Write-Host "  Target: $($TargetConfig.User)@$($TargetConfig.Host) (via tunnel)"
    
    # Test router connection
    if (-not (Test-SSHConnection -Config $RouterConfig)) {
        throw "Router SSH connection test failed"
    }
    
    # Start tunnel
    $tunnelPort = $TargetConfig.TunnelPort
    Write-Host "Starting tunnel on port $tunnelPort..."
    
    $tunnelProcess = Start-SSHTunnel -RouterConfig $RouterConfig -TargetConfig $TargetConfig
    
    try {
        # Wait for tunnel to establish
        Start-Sleep -Seconds 3
        
        # Test target connection through tunnel
        $tunnelSSHConfig = @{
            Host = "127.0.0.1"
            Port = $tunnelPort
            User = $TargetConfig.User
            KeyFile = $TargetConfig.KeyFile
            HostKey = $TargetConfig.HostKey
            Password = $TargetConfig.Password
        }
        
        if (-not (Test-SSHConnection -Config $tunnelSSHConfig)) {
            throw "Target SSH connection through tunnel failed"
        }
        
        # Deploy through tunnel (same as direct SSH but through localhost:tunnelPort)
        Deploy-DirectSSH -DeployConfig $DeployConfig -FilesToDeploy $FilesToDeploy -RemotePath $RemotePath -SSHConfig $tunnelSSHConfig
        
    } finally {
        # Clean up tunnel
        if ($tunnelProcess) {
            Stop-SSHTunnel -TunnelProcess $tunnelProcess
        }
    }
    
    return $true
}

# ------------------------------
# SSH Helper Functions
# ------------------------------
function Test-SSHConnection {
    param([hashtable] $Config)
    
    # Build plink arguments for PowerShell 5 compatibility
    $plinkArgs = @()
    $plinkArgs += "-batch"
    $plinkArgs += "-o"
    $plinkArgs += "ConnectTimeout=10"
    
    if ($Config.KeyFile -and (Test-Path $Config.KeyFile)) {
        $plinkArgs += "-i"
        $plinkArgs += $Config.KeyFile
    }
    
    if ($Config.HostKey) {
        $plinkArgs += "-hostkey"
        $plinkArgs += $Config.HostKey
    }
    
    if ($Config.Port -and $Config.Port -ne "22") {
        $plinkArgs += "-P"
        $plinkArgs += $Config.Port
    }
    
    # Add connection string and test command
    $plinkArgs += "$($Config.User)@$($Config.Host)"
    $plinkArgs += "echo SSH_TEST_SUCCESS"
    
    try {
        # Use cmd /c to ensure proper exit code handling in PowerShell 5
        $output = & cmd /c "plink.exe $($plinkArgs -join ' ') 2>&1"
        $success = ($LASTEXITCODE -eq 0) -and ($output -like "*SSH_TEST_SUCCESS*")
        return $success
    } catch {
        Write-Warning "SSH connection test failed: $($_.Exception.Message)"
        return $false
    }
}

function Invoke-SSHCommand {
    param(
        [hashtable] $Config,
        [string] $Command
    )
    
    # Build plink arguments for PowerShell 5 compatibility
    $plinkArgs = @()
    $plinkArgs += "-batch"
    
    if ($Config.KeyFile -and (Test-Path $Config.KeyFile)) {
        $plinkArgs += "-i"
        $plinkArgs += $Config.KeyFile
    }
    
    if ($Config.HostKey) {
        $plinkArgs += "-hostkey"
        $plinkArgs += $Config.HostKey
    }
    
    if ($Config.Port -and $Config.Port -ne "22") {
        $plinkArgs += "-P"
        $plinkArgs += $Config.Port
    }
    
    # Add connection string and command
    $plinkArgs += "$($Config.User)@$($Config.Host)"
    $plinkArgs += $Command
    
    # Use cmd /c for better exit code handling in PowerShell 5
    & cmd /c "plink.exe $($plinkArgs -join ' ')"
    return $LASTEXITCODE
}

function Start-SSHTunnel {
    param(
        [hashtable] $RouterConfig,
        [hashtable] $TargetConfig
    )
    
    # Build plink arguments for tunnel
    $plinkArgs = @()
    $plinkArgs += "-batch"
    $plinkArgs += "-N"
    $plinkArgs += "-L"
    $plinkArgs += "$($TargetConfig.TunnelPort):$($TargetConfig.Host):22"
    
    if ($RouterConfig.KeyFile -and (Test-Path $RouterConfig.KeyFile)) {
        $plinkArgs += "-i"
        $plinkArgs += $RouterConfig.KeyFile
    }
    
    if ($RouterConfig.HostKey) {
        $plinkArgs += "-hostkey"
        $plinkArgs += $RouterConfig.HostKey
    }
    
    $plinkArgs += "$($RouterConfig.User)@$($RouterConfig.Host)"
    
    Write-Host "Starting tunnel: plink.exe $($plinkArgs -join ' ')"
    
    # Use Start-Process for PowerShell 5 compatibility
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "plink.exe"
    $processInfo.Arguments = $plinkArgs -join " "
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    $process.Start() | Out-Null
    
    # Return process object instead of job for PowerShell 5 compatibility
    return $process
}

function Stop-SSHTunnel {
    param($TunnelProcess)
    
    if ($TunnelProcess -and (-not $TunnelProcess.HasExited)) {
        Write-Host "Stopping SSH tunnel..."
        try {
            $TunnelProcess.Kill()
            $TunnelProcess.WaitForExit(5000) # Wait up to 5 seconds
        } catch {
            Write-Warning "Failed to stop SSH tunnel: $($_.Exception.Message)"
        }
        finally {
            if ($TunnelProcess) {
                $TunnelProcess.Dispose()
            }
        }
    }
}
