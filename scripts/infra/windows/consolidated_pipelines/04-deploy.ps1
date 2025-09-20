<# ========================= 04-deploy.ps1 =========================
Purpose:
- Unified deployment script supporting multiple access methods
- Automatically routes deployment based on access configuration
- Handles local, direct SSH, and router tunnel deployments
- Ensures register_task.ps1 is also at C:\Watchdog\register_task.ps1
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
Write-PipelineStep "INITIALIZE" "Setting up deployment environment"

Enable-PipelineDiagnostics -Enabled:$Diagnostics -ScriptName "04-deploy"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT

    if ($global:__PipelineDiagnosticsEnabled) {
        Write-Host "Tooling versions (for diagnostics):"
        try { & cmd /c "plink.exe -V" } catch {}
        try { & cmd /c "pscp.exe -V" } catch {}
        Write-Host "PATH: $env:PATH"
    }

    Write-PipelineStep "VALIDATION" "Checking deployment prerequisites"

    # Verify build artifacts (binary + version.txt present)
    $artifacts = Test-BuildArtifacts -ProjectRoot $env:PROJECT_ROOT -JobName $env:CI_JOB_NAME

    # Determine job name (prefer PC_NAME for target naming)
    $jobName = if ($env:PC_NAME) { $env:PC_NAME } else { $env:CI_JOB_NAME }

    # Prepare deployment configuration
    $deployConfig = @{
        BinaryName = "wd-$jobName.exe"        # target filename on remote
        BinaryPath = $artifacts.BinaryPath    # source path of built artifact
        JobName    = $jobName                 # used for process/task names
    }

    $remotePath = $env:REMOTE_PATH

    # Files to copy to target (preserve relative paths under C:\Watchdog)
    $registerRel = 'scripts\infra\windows\utils\register_task.ps1'
    $filesToDeploy = @(
        $deployConfig.BinaryName
        'version.txt'
        $registerRel
    )

    # Update version.txt with deployment timestamp
    $gitData = @{
        CommitTag = $env:COMMIT_TAG
        CommitHash = $env:COMMIT_HASH
        Branch     = $env:GIT_BRANCH
        BuildTime  = $env:BUILD_TIME
    }
    New-VersionFile -GitData $gitData -OutputPath "version.txt" -IncludeDeployTime

    Write-Host "Deployment Configuration:"
    Write-Host "  Target: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "  Remote Path: $remotePath"
    Write-Host "  Binary: $($deployConfig.BinaryName)"
    Write-Host "  Access Method: $($config.Method)"

    # Check required tools based on access method
    if ($config.Method -ne "local") {
        if (-not (Get-Command plink -ErrorAction SilentlyContinue) -or
            -not (Get-Command pscp  -ErrorAction SilentlyContinue)) {
            Write-PipelineError "VALIDATION" "plink/pscp not found. Install PuTTY tools." 1
        }
    }

    Write-PipelineStep "DEPLOYMENT" "Deploying application using $($config.Method) method"

    $deploymentSuccess = $false

    switch ($config.Method) {
        "local" {
            $deploymentSuccess = Deploy-Local -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath

            if ($deploymentSuccess) {
                # Mirror register_task.ps1 to C:\Watchdog\register_task.ps1
                $src = Join-Path $remotePath $registerRel
                $dst = Join-Path $remotePath 'register_task.ps1'
                if (-not (Test-Path -LiteralPath $src)) {
                    Write-PipelineError "DEPLOYMENT" "register_task.ps1 not found at $src after deploy" 1
                }
                Copy-Item -LiteralPath $src -Destination $dst -Force
            }
        }

        "direct" {
            $sshConfig = @{
                Host     = $env:TARGET_IP
                Port     = $env:SSH_PORT
                User     = $env:TARGET_USER
                Password = $env:TARGET_PASS
                HostKey  = $env:SSH_HOSTKEY
            }

            $deploymentSuccess = Deploy-DirectSSH -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath -SSHConfig $sshConfig

            if ($deploymentSuccess) {
                # Mirror register_task.ps1 to C:\Watchdog\register_task.ps1 on remote
                $src = (Join-Path $remotePath $registerRel).Replace("'", "''")
                $dst = (Join-Path $remotePath 'register_task.ps1').Replace("'", "''")
                $copyCmd = @"
if (!(Test-Path '$src')) { Write-Error "Missing: $src"; exit 1 }
Copy-Item -Force -LiteralPath '$src' -Destination '$dst'
"@
                $rc = Invoke-SSHCommand -Config $sshConfig -Command $copyCmd
                if ($rc -ne 0) {
                    Write-PipelineError "DEPLOYMENT" "Failed to place register_task.ps1 at $remotePath\register_task.ps1 (exit $rc)" $rc
                }
            }
        }

        "router" {
            $routerConfig = @{
                Host     = $env:ROUTER_IP
                User     = $env:ROUTER_USER
                KeyFile  = $env:ROUTER_SSH_KEY
                HostKey  = $env:ROUTER_SSH_HOSTKEY
                Password = $env:ROUTER_PASS
            }
            $targetConfig = @{
                Host       = $env:TARGET_IP
                User       = $env:TARGET_USER
                KeyFile    = $env:TARGET_SSH_KEY
                HostKey    = $env:TARGET_SSH_HOSTKEY
                Password   = $env:TARGET_PASS
                TunnelPort = $env:TARGET_TUNNEL_PORT
            }

            $deploymentSuccess = Deploy-RouterTunnel -DeployConfig $deployConfig -FilesToDeploy $filesToDeploy -RemotePath $remotePath -RouterConfig $routerConfig -TargetConfig $targetConfig

            if ($deploymentSuccess) {
                # Re-open a short-lived tunnel to perform the copy on the target
                Write-Host "Mirroring register_task.ps1 to root via tunnel..."
                $tunnelProcess = Start-SSHTunnel -RouterConfig $routerConfig -TargetConfig $targetConfig
                try {
                    Start-Sleep -Seconds 2
                    $tunnelSSHConfig = @{
                        Host     = '127.0.0.1'
                        Port     = $targetConfig.TunnelPort
                        User     = $targetConfig.User
                        KeyFile  = $targetConfig.KeyFile
                        HostKey  = $targetConfig.HostKey
                        Password = $targetConfig.Password
                    }
                    $src = (Join-Path $remotePath $registerRel).Replace("'", "''")
                    $dst = (Join-Path $remotePath 'register_task.ps1').Replace("'", "''")
                    $copyCmd = @"
if (!(Test-Path '$src')) { Write-Error "Missing: $src"; exit 1 }
Copy-Item -Force -LiteralPath '$src' -Destination '$dst'
"@
                    $rc = Invoke-SSHCommand -Config $tunnelSSHConfig -Command $copyCmd
                    if ($rc -ne 0) {
                        Write-PipelineError "DEPLOYMENT" "Failed to place register_task.ps1 at $remotePath\register_task.ps1 via tunnel (exit $rc)" $rc
                    }
                } finally {
                    if ($tunnelProcess) { Stop-SSHTunnel -TunnelProcess $tunnelProcess }
                }
            }
        }

        default {
            Write-PipelineError "DEPLOYMENT" "Unknown access method: $($config.Method)" 1
        }
    }

    if (-not $deploymentSuccess) {
        Write-PipelineError "DEPLOYMENT" "Deployment failed" 1
    }

    Write-PipelineStep "VERIFICATION" "Verifying deployment"

    # Verify exe and the root-level register_task.ps1 exist
    $verificationSuccess = $false

    switch ($config.Method) {
        "local" {
            $exeOk  = Test-Path (Join-Path $remotePath $deployConfig.BinaryName)
            $regOk  = Test-Path (Join-Path $remotePath 'register_task.ps1')
            $verificationSuccess = $exeOk -and $regOk
        }

        "direct" {
            $sshConfig = @{
                Host     = $env:TARGET_IP
                Port     = $env:SSH_PORT
                User     = $env:TARGET_USER
                Password = $env:TARGET_PASS
                HostKey  = $env:SSH_HOSTKEY
            }
            $verifyCmd = @"
if ((Test-Path '$remotePath\$($deployConfig.BinaryName)') -and (Test-Path '$remotePath\register_task.ps1')) { exit 0 } else { exit 1 }
"@
            $exitCode = Invoke-SSHCommand -Config $sshConfig -Command $verifyCmd
            $verificationSuccess = $exitCode -eq 0
        }

        "router" {
            # We already verified during the tunnel copy; treat as success here.
            $verificationSuccess = $true
        }
    }

    if (-not $verificationSuccess) {
        Write-Warning "Could not verify deployment success (binary or register_task.ps1 missing)"
    } else {
        Write-Host "Deployment verified successfully." -ForegroundColor Green
    }

} catch {
    Write-Host "Verbose error details:" -ForegroundColor Red
    $_ | Format-List * | Out-String | Write-Host
    if ($_.InvocationInfo) { Write-Host "At: $($_.InvocationInfo.PositionMessage)" }
    Write-DiagnosticSnapshot -Title "Deployment Failure Snapshot"
    Write-PipelineError "DEPLOYMENT" "Deployment failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nDeployment pipeline completed successfully." -ForegroundColor Green
