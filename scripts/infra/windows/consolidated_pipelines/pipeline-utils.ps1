<# ========================= pipeline-utils.ps1 =========================
Purpose:
- Shared utility functions for all pipeline operations
- Common project setup, Git metadata extraction, and build helpers
- Environment detection and configuration
================================================================ #>

# ------------------------------
# Project Root Detection
# ------------------------------
function Get-ProjectRoot {
    param([string] $Start = $PSScriptRoot)

    # Find repo boundary if possible (folder containing .git)
    $repoTop = $null
    try {
        $gitTop = (git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and $gitTop) {
            $repoTop = (Resolve-Path -LiteralPath $gitTop).Path
        }
    } catch {}

    # Walk upward starting at $Start, but do not go above $repoTop (if known)
    $dir = Get-Item -LiteralPath $Start
    while ($dir) {
        $pp = Join-Path $dir.FullName 'pyproject.toml'
        if (Test-Path -LiteralPath $pp) {
            return $dir.FullName
        }

        # If we know repoTop, stop once we reach it (after checking it)
        if ($repoTop -and ((Resolve-Path -LiteralPath $dir.FullName).Path -ieq $repoTop)) {
            break
        }
        $dir = $dir.Parent
    }

    # If we know repoTop, as a last try, accept it if it has pyproject.toml
    if ($repoTop -and (Test-Path -LiteralPath (Join-Path $repoTop 'pyproject.toml'))) {
        return $repoTop
    }

    throw "Could not locate project root (no pyproject.toml found; start='$Start', repoTop='$repoTop')."
}

# ------------------------------
# Git Metadata Collection
# ------------------------------
function Get-GitMetadata {
    $gitData = @{}
    
    try {
        $gitData.CommitTag = git describe --tags --always
        $gitData.Branch = git rev-parse --abbrev-ref HEAD
        $gitData.CommitHash = git rev-parse HEAD
        $gitData.BuildTime = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
        $gitData.Success = $true
        
        Write-Host "Git Metadata:"
        Write-Host "  Commit Tag: $($gitData.CommitTag)"
        Write-Host "  Branch: $($gitData.Branch)"
        Write-Host "  Commit Hash: $($gitData.CommitHash)"
        Write-Host "  Build Time: $($gitData.BuildTime)"
    } catch {
        Write-Warning "Git not found or not a Git repository."
        $gitData.Success = $false
    }
    
    return $gitData
}

# ------------------------------
# Secure Password Loading
# ------------------------------
function Get-SecurePassword {
    param(
        [string] $PasswordFilePath,
        [string] $Description = "password"
    )
    
    try {
        if (Test-Path -LiteralPath $PasswordFilePath) {
            $raw = (Get-Content -LiteralPath $PasswordFilePath -Raw).Trim()
            if (-not $raw) { return $null }

            # Try to interpret as a protected secure string first (output of ConvertFrom-SecureString)
            try {
                $securePassword = $raw | ConvertTo-SecureString
                $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
                return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
            } catch {
                # Fallback: treat file as plain text password
                Write-Verbose "Using plain-text $Description loaded from $PasswordFilePath"
                return $raw
            }
        } else {
            Write-Warning "$Description file not found: $PasswordFilePath"
            return $null
        }
    } catch {
        Write-Warning "Failed to load $Description from $PasswordFilePath. ($($_.Exception.Message))"
        return $null
    }
}

# ------------------------------
# Python Environment Helpers
# ------------------------------
function Get-PipInstallTarget {
    param([string[]] $Extras)
    
    if (-not $Extras -or $Extras.Count -eq 0) { 
        return "." 
    }
    $joined = ($Extras -join ",")
    return ".[$joined]"
}

function New-PythonVirtualEnv {
    param(
        [string] $VenvName,
        [string] $ProjectRoot
    )
    
    $venvPath = Join-Path $ProjectRoot $VenvName
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    
    # Cleanup existing environment
    if (Test-Path $venvPath) {
        Remove-Item -Recurse -Force $venvPath
    }
    
    Write-Host "Creating virtual environment: $VenvName"
    python -m venv $venvPath
    
    if (-not (Test-Path $pythonExe)) {
        throw "Failed to create virtual environment at $venvPath"
    }
    
    # Activate environment
    . $activateScript
    
    Write-Host "Upgrading pip/setuptools/wheel..."
    & $pythonExe -m pip install -U pip setuptools wheel
    
    return @{
        Path = $venvPath
        Python = $pythonExe
        Activate = $activateScript
    }
}

# ------------------------------
# Build Helpers
# ------------------------------
function Get-DevicesForPC {
    param([string] $PCName, [string] $ProjectRoot)
    
    try {
        $devices = python -c "import sys; from importlib.metadata import entry_points; eps = entry_points(group='ipat_watchdog.pc_plugins'); names = [ep.name for ep in eps if ep.name == '$PCName']; print(','.join(names))"
        return $devices -split ',' | ForEach-Object { $_.Trim() }
    } catch {
        Write-Warning "Failed to load PC plugins from pyproject.toml entry points."
        return @()
    }
}

function New-VersionFile {
    param(
        [hashtable] $GitData,
        [string] $OutputPath,
        [switch] $IncludeDeployTime
    )
    
    $content = @"
COMMIT_TAG=$($GitData.CommitTag)
COMMIT_HASH=$($GitData.CommitHash)
GIT_BRANCH=$($GitData.Branch)
BUILD_TIME=$($GitData.BuildTime)
"@

    if ($IncludeDeployTime) {
        $content += "`nDEPLOY_TIME=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')Z"
    }
    
    $content | Out-File -Encoding ascii $OutputPath -Force
}

# ------------------------------
# Access Method Detection (PowerShell 5 Compatible)
# ------------------------------
function Get-AccessMethod {
    param([string] $ConfigFile)
    
    # Read access method from config file or environment
    if (Test-Path $ConfigFile) {
        $config = Get-Content $ConfigFile | ConvertFrom-StringData -ErrorAction SilentlyContinue
        if ($config -and $config.ACCESS_METHOD) {
            switch ($config.ACCESS_METHOD.ToLower()) {
                "local" { return "local" }
                "direct" { return "direct" }
                "router" { return "router" }
                default { return "direct" }
            }
        }
    }
    
    # Default fallback
    return "direct"
}

# ------------------------------
# Validation Helpers
# ------------------------------
function Test-BuildArtifacts {
    param(
        [string] $ProjectRoot,
        [string] $JobName
    )
    
    $binaryName = "wd-${JobName}.exe"
    $distPath = Join-Path $ProjectRoot "dist\$binaryName"
    $versionPath = Join-Path $ProjectRoot "version.txt"
    
    $missing = @()
    if (-not (Test-Path $distPath)) { $missing += $distPath }
    if (-not (Test-Path $versionPath)) { $missing += $versionPath }
    
    if ($missing.Count -gt 0) {
        throw "Missing build artifacts: $($missing -join ', ')"
    }
    
    return @{
        BinaryPath = $distPath
        VersionPath = $versionPath
        BinaryName = $binaryName
    }
}

# ------------------------------
# Logging Helpers
# ------------------------------
function Write-PipelineStep {
    param(
        [string] $Step,
        [string] $Message
    )
    
    Write-Host "`n== $Step ==" -ForegroundColor Green
    if ($Message) {
        Write-Host $Message
    }
}

function Write-PipelineError {
    param(
        [string] $Step,
        [string] $Message,
        [int] $ExitCode = 1
    )
    
    Write-Host "`n!! $Step FAILED !!" -ForegroundColor Red
    Write-Error $Message
    if ($ExitCode -gt 0) {
        exit $ExitCode
    }
}

# ------------------------------
# Timer Helpers
# ------------------------------
function Start-PipelineTimer {
    return Get-Date
}

function Stop-PipelineTimer {
    param([datetime] $StartTime)
    
    $endTime = Get-Date
    $duration = $endTime - $StartTime
    Write-Host "`nElapsed time: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Cyan
    return $duration
}

# ------------------------------
# Diagnostics Helpers
# ------------------------------
function Enable-PipelineDiagnostics {
    param(
        [switch] $Enabled,
        [string] $ScriptName = "pipeline",
        [string] $LogDir = $null
    )

    if (-not $Enabled) { return }

    try {
        if (-not $LogDir) {
            if ($env:PROJECT_ROOT -and (Test-Path -LiteralPath $env:PROJECT_ROOT)) {
                $LogDir = Join-Path $env:PROJECT_ROOT 'build\logs'
            } else {
                $LogDir = Join-Path $PSScriptRoot 'logs'
            }
        }
        if (-not (Test-Path -LiteralPath $LogDir)) {
            New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
        }

        $script:PipelineLogPath = Join-Path $LogDir ("{0}-{1:yyyyMMdd-HHmmss}.log" -f $ScriptName, (Get-Date))
        Set-StrictMode -Version Latest
        $global:ErrorActionPreference = 'Stop'
        $global:VerbosePreference = 'Continue'
        $global:DebugPreference = 'Continue'
        try { Start-Transcript -Path $script:PipelineLogPath -Append | Out-Null } catch {}
        $global:__PipelineDiagnosticsEnabled = $true

        Write-Host "Diagnostics enabled. Transcript: $script:PipelineLogPath"
    } catch {
        Write-Warning "Failed to enable diagnostics: $($_.Exception.Message)"
    }
}

function Disable-PipelineDiagnostics {
    if ($global:__PipelineDiagnosticsEnabled) {
        try { Stop-Transcript | Out-Null } catch {}
        $global:__PipelineDiagnosticsEnabled = $false
    }
}

function Write-DiagnosticSnapshot {
    param(
        [string] $Title = "Diagnostic Snapshot"
    )
    try {
        Write-Host "==== $Title ====" -ForegroundColor Yellow
        Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        Write-Host "PWD: $(Get-Location)"
        if ($PSVersionTable) {
            Write-Host "PSVersion: $($PSVersionTable.PSVersion)"
        }
        Write-Host "User: $env:USERNAME"
        Write-Host "PROJECT_ROOT: $env:PROJECT_ROOT"
        Write-Host "CI_JOB_NAME: $env:CI_JOB_NAME"
        Write-Host "PC_NAME: $env:PC_NAME"
        if ($env:PC_DEVICES) { Write-Host "PC_DEVICES: $env:PC_DEVICES" }
        if ($env:COMMIT_TAG) { Write-Host "Commit: $env:COMMIT_TAG ($env:COMMIT_HASH) on $env:GIT_BRANCH @ $env:BUILD_TIME" }
        if ($global:PipelineLogPath) { Write-Host "Transcript: $global:PipelineLogPath" }
        if ($Error.Count -gt 0) {
            Write-Host "Last Error (raw):" -ForegroundColor Red
            $Error[0] | Format-List * | Out-String | Write-Host
        }
        Write-Host "=========================="
    } catch {
        Write-Warning "Failed to write diagnostic snapshot: $($_.Exception.Message)"
    }
}
