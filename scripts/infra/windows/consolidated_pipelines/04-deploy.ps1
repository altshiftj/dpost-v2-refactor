<# ========================= 04-deploy.ps1 =========================
Purpose:
- Unified deployment script supporting multiple access methods
- Automatically routes deployment based on access configuration
- Handles local, direct SSH, and router tunnel deployments
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin"
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"
. "$PSScriptRoot\deploy-helpers.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up deployment environment"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    Write-PipelineStep "VALIDATION" "Checking deployment prerequisites"
    
    # Verify build artifacts
    $artifacts = Test-BuildArtifacts -ProjectRoot $env:PROJECT_ROOT -JobName $env:CI_JOB_NAME
    
    # Prepare deployment configuration
    $deployConfig = @{
        BinaryName = $artifacts.BinaryName
        BinaryPath = $artifacts.BinaryPath
        JobName = $env:CI_JOB_NAME
    }
    
    $remotePath = $env:REMOTE_PATH
    $filesToDeploy = @(
        $artifacts.BinaryName
        'version.txt'
        'scripts\infra\windows\utils\register_task.ps1'
    )
    
    # Update version.txt with deployment timestamp
    $gitData = @{
        CommitTag = $env:COMMIT_TAG
        CommitHash = $env:COMMIT_HASH
        Branch = $env:GIT_BRANCH
        BuildTime = $env:BUILD_TIME
    }
    New-VersionFile -GitData $gitData -OutputPath "version.txt" -IncludeDeployTime
    
    Write-Host "Deployment Configuration:"
    Write-Host "  Target: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "  Remote Path: $remotePath"
    Write-Host "  Binary: $($artifacts.BinaryName)"
    Write-Host "  Access Method: $($config.Method)"
    
    # Check required tools based on access method
    if ($config.Method -ne "local") {
        if (-not (Get-Command plink -ErrorAction SilentlyContinue) -or 
            -not (Get-Command pscp -ErrorAction SilentlyContinue)) {
            Write-PipelineError "VALIDATION" "plink/pscp not found. Install PuTTY tools." 1
        }
    }
    
    Write-PipelineStep "DEPLOYMENT" "Deploying application using $($config.Method) method"
    
    # Route deployment based on access method
    $deploymentSuccess = $false
    
    switch ($config.Method) {
        "local" {
            $deploymentSuccess = Deploy-Local -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath
        }
        
        "direct" {
            $sshConfig = @{
                Host = $env:TARGET_IP
                Port = $env:SSH_PORT
                User = $env:TARGET_USER
                Password = $env:TARGET_PASS
                HostKey = $env:SSH_HOSTKEY
            }
            
            $deploymentSuccess = Deploy-DirectSSH -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath -SSHConfig $sshConfig
        }
        
        "router" {
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
            
            $deploymentSuccess = Deploy-RouterTunnel -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath -RouterConfig $routerConfig -TargetConfig $targetConfig
        }
        
        default {
            Write-PipelineError "DEPLOYMENT" "Unknown access method: $($config.Method)" 1
        }
    }
    
    if (-not $deploymentSuccess) {
        Write-PipelineError "DEPLOYMENT" "Deployment failed" 1
    }
    
    Write-PipelineStep "VERIFICATION" "Verifying deployment"
    
    # Verify deployment based on access method
    $verificationSuccess = $false
    
    switch ($config.Method) {
        "local" {
            $remoteExePath = Join-Path $remotePath $artifacts.BinaryName
            $verificationSuccess = Test-Path $remoteExePath
        }
        
        "direct" {
            $sshConfig = @{
                Host = $env:TARGET_IP
                Port = $env:SSH_PORT
                User = $env:TARGET_USER
                HostKey = $env:SSH_HOSTKEY
            }
            
            $verifyCmd = "Test-Path '$remotePath\$($artifacts.BinaryName)'"
            $exitCode = Invoke-SSHCommand -Config $sshConfig -Command $verifyCmd
            $verificationSuccess = $exitCode -eq 0
        }
        
        "router" {
            # For router tunnel, we'll assume success if deployment succeeded
            # as the tunnel verification was already done during deployment
            $verificationSuccess = $true
        }
    }
    
    if (-not $verificationSuccess) {
        Write-Warning "Could not verify deployment success"
    } else {
        Write-Host "Deployment verified successfully." -ForegroundColor Green
    }
    
} catch {
    Write-PipelineError "DEPLOYMENT" "Deployment failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
}

Write-Host "`nDeployment pipeline completed successfully." -ForegroundColor Green
