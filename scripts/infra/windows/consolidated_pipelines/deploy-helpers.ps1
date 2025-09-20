<# ========================= deploy-helpers.ps1 =========================
Purpose:
- Deployment helpers for different access methods
- Handles local, direct SSH, and router tunnel deployments
- Common deployment logic with method-specific implementations
================================================================ #>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-MaskedArgs {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$InputArgs)
    if ($null -eq $InputArgs) { return '' }
    $arr = @()
    foreach ($a in $InputArgs) {
        if ($a -is [System.Array]) { $arr += @($a) }
        else { $arr += @("$a") }
    }
    $mask = @()
    for ($i=0; $i -lt $arr.Count; $i++) {
        if ($arr[$i] -eq '-pw' -and ($i+1) -lt $arr.Count) { $mask += '-pw'; $mask += '*****'; $i++ } else { $mask += $arr[$i] }
    }
    return ($mask -join ' ')
}

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

    if (-not (Test-Path -LiteralPath $RemotePath)) {
        New-Item -Path $RemotePath -Force -ItemType Directory | Out-Null
    }

    try {
        $taskPrimary = "IPAT-Watchdog-$($DeployConfig.JobName)"
        $taskFallback = 'IPAT-Watchdog'
        Stop-ScheduledTask -TaskName $taskPrimary -ErrorAction SilentlyContinue
        Stop-ScheduledTask -TaskName $taskFallback -ErrorAction SilentlyContinue
    $exePath = Join-Path $RemotePath $DeployConfig.BinaryName
        Get-Process | Where-Object { $_.Path -eq $exePath } | Stop-Process -Force
    } catch {
        Write-Warning "Failed to stop running instances: $($_.Exception.Message)"
    }

    foreach ($file in $FilesToDeploy[0..1]) { # backup only binary and version.txt
        $targetPath = Join-Path $RemotePath $file
        if (Test-Path -LiteralPath $targetPath) {
            $backupPath = $targetPath -replace '\\.(\w+)$', '_backup.$1'
            try {
                if (Test-Path -LiteralPath $backupPath) { Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue }
                Rename-Item -Path $targetPath -NewName $backupPath -Force -ErrorAction Stop
            } catch {
                Write-Warning "Initial backup rename failed for '$file': $($_.Exception.Message). Retrying after removing any existing backup."
                try {
                    if (Test-Path -LiteralPath $backupPath) { Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue }
                    Start-Sleep -Milliseconds 200
                    Rename-Item -Path $targetPath -NewName $backupPath -Force -ErrorAction Stop
                } catch {
                    throw "Failed to create backup for '$file': $($_.Exception.Message)"
                }
            }
            Write-Host "Backed up: $file -> $([System.IO.Path]::GetFileName($backupPath))"
        }
    }

    foreach ($file in $FilesToDeploy) {
        $sourcePath = if ($file -eq $DeployConfig.BinaryName) { $DeployConfig.BinaryPath } else { $file }
        $targetPath = Join-Path $RemotePath $file
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        Write-Host "Copied: $file"
    }

    return $true
}

# ------------------------------
# SSH Helper Functions
# ------------------------------
function New-PlinkBaseArgs {
    param([hashtable]$Config, [string]$LogPrefix)
    $argList = @('-batch','-ssh')
    if ($global:__PipelineDiagnosticsEnabled) { $argList += '-v' }
    if ($Config.ContainsKey('KeyFile') -and $Config.KeyFile -and (Test-Path -LiteralPath $Config.KeyFile)) { $argList += '-i'; $argList += $Config.KeyFile }
    if ($Config.ContainsKey('HostKey') -and $Config.HostKey) { $argList += '-hostkey'; $argList += $Config.HostKey }
    if ($Config.ContainsKey('Port') -and $Config.Port -and $Config.Port -ne '22') { $argList += '-P'; $argList += $Config.Port }
    if ($Config.ContainsKey('Password') -and $Config.Password) { $argList += '-pw'; $argList += $Config.Password }
    if ($global:__PipelineDiagnosticsEnabled) {
        $logDir = if ($env:PROJECT_ROOT) { Join-Path $env:PROJECT_ROOT 'build\logs' } else { Join-Path $PSScriptRoot 'logs' }
        if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        $sshLogPath = Join-Path $logDir ("$LogPrefix-{0}-{1:yyyyMMdd-HHmmss}.log" -f $Config.Host, (Get-Date))
        $argList += '-sshlog'; $argList += $sshLogPath
    }
    return ,$argList
}

function Test-SSHConnection {
    param([hashtable] $Config)

    $plinkArgs = New-PlinkBaseArgs -Config $Config -LogPrefix 'plink-test'
    $plinkArgs += ("{0}@{1}" -f $Config.User, $Config.Host)
    $plinkArgs += 'echo SSH_TEST_SUCCESS'

    if ($global:__PipelineDiagnosticsEnabled) {
        Write-Host ("plink.exe {0}" -f (Write-MaskedArgs -InputArgs $plinkArgs))
    }

    $output = & cmd /c "plink.exe $($plinkArgs -join ' ') 2>&1"
    $exit = $LASTEXITCODE
    $success = ($exit -eq 0) -and ($output -like '*SSH_TEST_SUCCESS*')

    if (-not $success) {
        Write-Warning ("plink exit code: {0}" -f $exit)
        if ($output) {
            $preview = ($output -split "`n") | Select-Object -First 20
            Write-Warning ("plink output (first 20 lines):`n{0}" -f ($preview -join "`n"))
        }
    }
    return $success
}

function Invoke-SSHCommand {
    param(
        [hashtable] $Config,
        [string] $Command
    )

    $plinkArgs = New-PlinkBaseArgs -Config $Config -LogPrefix 'plink-cmd'

    $bytes = [System.Text.Encoding]::Unicode.GetBytes($Command)
    $encoded = [Convert]::ToBase64String($bytes)
    $remoteCmd = "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"

    $plinkArgs += ("{0}@{1}" -f $Config.User, $Config.Host)
    $plinkArgs += $remoteCmd

    if ($global:__PipelineDiagnosticsEnabled) {
        Write-Host ("plink.exe {0}" -f (Write-MaskedArgs -InputArgs $plinkArgs))
    }

    $output = & cmd /c "plink.exe $($plinkArgs -join ' ') 2>&1"
    $exit = $LASTEXITCODE
    if ($exit -ne 0 -and $global:__PipelineDiagnosticsEnabled) {
        Write-Warning ("plink command exit code: {0}" -f $exit)
        if ($output) {
            $preview = ($output -split "`n") | Select-Object -First 40
            Write-Warning ("plink output (first 40 lines):`n{0}" -f ($preview -join "`n"))
        }
    }
    return $exit
}

function New-PscpBaseArgs {
    param([hashtable]$Config, [string]$LogPrefix)
    $argList = @('-batch','-scp')
    if ($global:__PipelineDiagnosticsEnabled) { $argList += '-v' }
    if ($Config.ContainsKey('Port') -and $Config.Port) { $argList += '-P'; $argList += $Config.Port }
    if ($Config.ContainsKey('Password') -and $Config.Password) { $argList += '-pw'; $argList += $Config.Password }
    if ($Config.ContainsKey('KeyFile') -and $Config.KeyFile -and (Test-Path -LiteralPath $Config.KeyFile)) { $argList += '-i'; $argList += $Config.KeyFile }
    if ($Config.ContainsKey('HostKey') -and $Config.HostKey) { $argList += '-hostkey'; $argList += $Config.HostKey }
    return ,$argList
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

    if (-not (Test-SSHConnection -Config $SSHConfig)) { throw "SSH connection test failed" }

    $createDirCmd = "if (!(Test-Path '$RemotePath')) { New-Item -ItemType Directory -Force -Path '$RemotePath' | Out-Null }"
    [void](Invoke-SSHCommand -Config $SSHConfig -Command $createDirCmd)

    # Emulate original admin remote prep exactly: stop+unregister tasks, sleep, kill by full path, rename to _backup
    $prepCmd = @"
`$p    = '$RemotePath'
`$exe  = '$($DeployConfig.BinaryName)'
`$path = Join-Path `$p `$exe

if (!(Test-Path `$p)) { New-Item `$p -ItemType Directory -Force | Out-Null }

Get-ScheduledTask | Where-Object { `$_.TaskName -like 'IPAT-Watchdog*' } |
    ForEach-Object {
        Stop-ScheduledTask       -TaskName `$_.TaskName -EA SilentlyContinue
        Unregister-ScheduledTask -TaskName `$_.TaskName -Confirm:`$false
    }
Start-Sleep 2

Get-Process -EA SilentlyContinue |
    Where-Object { `$_.Path -eq `$path } |
    Stop-Process -Force

foreach (`$f in @(`$exe,'version.txt')) {
    `$src = Join-Path `$p `$f
    if (Test-Path `$src) {
        `$bak = `$src -replace '\.(\w+)$','_backup.`$1'
        try {
            if (Test-Path `$bak) { Remove-Item `$bak -Force -EA SilentlyContinue }
            Rename-Item -Path `$src -NewName `$bak -Force -EA Stop
        } catch {
            try {
                if (Test-Path `$bak) { Remove-Item `$bak -Force -EA SilentlyContinue }
                Start-Sleep -Milliseconds 200
                Rename-Item -Path `$src -NewName `$bak -Force -EA Stop
            } catch {
                throw "Failed to create backup for '`$f': `$($_.Exception.Message)"
            }
        }
    }
}
"@
    [void](Invoke-SSHCommand -Config $SSHConfig -Command $prepCmd)

    if (-not (Get-Command pscp -ErrorAction SilentlyContinue)) { throw "pscp not available. Install PuTTY tools and ensure they are in PATH." }

    foreach ($file in $FilesToDeploy) {
    $sourcePath = if ($file -eq $DeployConfig.BinaryName) { $DeployConfig.BinaryPath } else { $file }
        # Ensure remote parent directory exists for nested paths
        $parentRel = [System.IO.Path]::GetDirectoryName($file)
        if ($parentRel -and $parentRel -ne '.' -and $parentRel -ne [string]::Empty) {
            $remoteDir = (Join-Path $RemotePath $parentRel)
            $mkDirCmd = "if (!(Test-Path '" + $remoteDir + "')) { New-Item -ItemType Directory -Force -Path '" + $remoteDir + "' | Out-Null }"
            [void](Invoke-SSHCommand -Config $SSHConfig -Command $mkDirCmd)
        }

    $dst = ("$RemotePath/$file").Replace('\\','/')
        $remote = ("{0}@{1}:`"{2}`"" -f $SSHConfig.User, $SSHConfig.Host, $dst)

        $pscpArgs = New-PscpBaseArgs -Config $SSHConfig -LogPrefix 'pscp-copy'
        $pscpArgs += $sourcePath
        $pscpArgs += $remote

        if ($global:__PipelineDiagnosticsEnabled) {
            Write-Host ("pscp.exe {0}" -f (Write-MaskedArgs -InputArgs $pscpArgs))
        }

    & cmd /c "pscp.exe $($pscpArgs -join ' ')"
        if ($LASTEXITCODE -ne 0) { throw "Failed to copy $file via SCP (exit code: $LASTEXITCODE)" }

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

    if (-not (Test-SSHConnection -Config $RouterConfig)) { throw "Router SSH connection test failed" }

    $tunnelPort = $TargetConfig.TunnelPort
    Write-Host "Starting tunnel on port $tunnelPort..."
    $tunnelProcess = Start-SSHTunnel -RouterConfig $RouterConfig -TargetConfig $TargetConfig

    try {
        Start-Sleep -Seconds 3

        $tunnelSSHConfig = @{
            Host = '127.0.0.1'
            Port = $tunnelPort
            User = $TargetConfig.User
            KeyFile = $TargetConfig.KeyFile
            HostKey = $TargetConfig.HostKey
            Password = $TargetConfig.Password
        }

        if (-not (Test-SSHConnection -Config $tunnelSSHConfig)) { throw "Target SSH connection through tunnel failed" }

        Deploy-DirectSSH -DeployConfig $DeployConfig -FilesToDeploy $FilesToDeploy -RemotePath $RemotePath -SSHConfig $tunnelSSHConfig
    } finally {
        if ($tunnelProcess) { Stop-SSHTunnel -TunnelProcess $tunnelProcess }
    }

    return $true
}

# ------------------------------
# Tunnel helpers
# ------------------------------
function Start-SSHTunnel {
    param(
        [hashtable] $RouterConfig,
        [hashtable] $TargetConfig
    )

    $plinkArgs = @('-batch','-N','-L')
    $plinkArgs += ("{0}:{1}:22" -f $TargetConfig.TunnelPort, $TargetConfig.Host)

    if ($RouterConfig.ContainsKey('KeyFile') -and $RouterConfig.KeyFile -and (Test-Path $RouterConfig.KeyFile)) { $plinkArgs += '-i'; $plinkArgs += $RouterConfig.KeyFile }
    if ($RouterConfig.ContainsKey('HostKey') -and $RouterConfig.HostKey) { $plinkArgs += '-hostkey'; $plinkArgs += $RouterConfig.HostKey }
    if ($RouterConfig.ContainsKey('Password') -and $RouterConfig.Password) { $plinkArgs += '-pw'; $plinkArgs += $RouterConfig.Password }

    $plinkArgs += ("{0}@{1}" -f $RouterConfig.User, $RouterConfig.Host)

    if ($global:__PipelineDiagnosticsEnabled) { Write-Host ("plink.exe {0}" -f (Write-MaskedArgs -InputArgs $plinkArgs)) }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'plink.exe'
    $psi.Arguments = ($plinkArgs -join ' ')
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    return $proc
}

function Stop-SSHTunnel {
    param($TunnelProcess)

    if ($TunnelProcess -and (-not $TunnelProcess.HasExited)) {
        Write-Host 'Stopping SSH tunnel...'
        try {
            $TunnelProcess.Kill()
            $TunnelProcess.WaitForExit(5000) | Out-Null
        } catch {
            Write-Warning "Failed to stop SSH tunnel: $($_.Exception.Message)"
        } finally {
            if ($TunnelProcess) { $TunnelProcess.Dispose() }
        }
    }
}
