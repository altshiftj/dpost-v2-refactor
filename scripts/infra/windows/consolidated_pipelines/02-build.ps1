<# ========================= 02-build.ps1 =========================
Purpose:
- Unified build script for all PC configurations
- Uses PC/device mapping system for dependency resolution
- Creates executable using PyInstaller with PC-specific configuration
- Adds a runtime hook so ipat_watchdog.build_config always exists
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    [Parameter(Mandatory = $false)]
    [string] $PCName,
    [switch] $Diagnostics
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up build environment"

Enable-PipelineDiagnostics -Enabled:$Diagnostics -ScriptName "02-build"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT

    # Resolve PC/Job name
    if (-not $PCName -or [string]::IsNullOrWhiteSpace($PCName)) {
        if ($env:PC_NAME) { $PCName = $env:PC_NAME }
        elseif ($env:CI_JOB_NAME) { $PCName = $env:CI_JOB_NAME }
        else { throw "PCName not provided. Pass -PCName or set PC_NAME/CI_JOB_NAME." }
    }

    # Keep legacy CI variable for spec selection
    $CI_JOB_NAME = $PCName
    # Export for downstream steps
    $env:PC_NAME = $PCName
    $CI_COMMIT_TAG = if ($env:CI_COMMIT_TAG) { $env:CI_JOB_NAME }
                     elseif ($env:COMMIT_TAG) { $env:COMMIT_TAG }
                     else { "vLocalTest" }

    Write-Host "Build Configuration:"
    Write-Host "  Job Name (PC): $CI_JOB_NAME"
    Write-Host "  Commit Tag: $CI_COMMIT_TAG"

    Write-PipelineStep "BUILD SETUP" "Creating build environment"

    # Create/activate virtual environment
    $venv = New-PythonVirtualEnv -VenvName ".test_buildvenv" -ProjectRoot $env:PROJECT_ROOT
    Write-DiagnosticSnapshot -Title "After venv creation"

    Write-PipelineStep "DEPENDENCIES" "Installing build dependencies"

    # Get devices for this PC and install dependencies
    Write-Host "Getting devices for PC: $PCName"
    $devices = Get-DevicesForPC -PCName $PCName -ProjectRoot $env:PROJECT_ROOT
    if ($devices -and $devices.Count -gt 0) {
        Write-Host "Devices for $PCName`: $($devices -join ', ')"
    } else {
        Write-Host "No devices defined for $PCName" -ForegroundColor Yellow
    }

    $deviceExtras = $devices
    $allExtras = @('build') + $deviceExtras + @($PCName)

    $pipTarget = Get-PipInstallTarget -Extras $allExtras
    Write-Host "Installing project with extras: $pipTarget"
    $pipArgs = @('-m','pip','install','-e', $pipTarget)
    if ($Diagnostics) { $pipArgs += '--verbose' }
    & $venv.Python @pipArgs

    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "DEPENDENCIES" "Failed to install build dependencies" $LASTEXITCODE
    }

    Write-PipelineStep "VERSION FILE" "Creating version metadata"

    # Create version file
    $gitData = @{
        CommitTag = $env:COMMIT_TAG
        CommitHash = $env:COMMIT_HASH
        Branch     = $env:GIT_BRANCH
        BuildTime  = $env:BUILD_TIME
    }

    New-VersionFile -GitData $gitData -OutputPath "version.txt"
    if (-not (Test-Path -LiteralPath "build")) { New-Item -ItemType Directory -Path "build" -Force | Out-Null }
    Copy-Item -Force "version.txt" "build/version.txt"

    # --- Build-time config (dev convenience): src/ipat_watchdog/build_config.py ---
    # Kept for local runs / tests; will be cleaned up in finally.
    $buildConfigPath = Join-Path $env:PROJECT_ROOT "src\ipat_watchdog\build_config.py"
    $buildConfigContent = @(
        "# Auto-generated at build time. Do not commit.",
        "PC_NAME = '" + $PCName + "'"
    ) -join [Environment]::NewLine
    $null = New-Item -Path (Split-Path $buildConfigPath) -ItemType Directory -Force -ErrorAction SilentlyContinue
    Set-Content -Path $buildConfigPath -Value $buildConfigContent -Encoding UTF8
    Write-Host "Generated: $buildConfigPath"

    # --- Runtime hook to inject ipat_watchdog.build_config inside the frozen app ---
    $rthDir  = Join-Path $env:PROJECT_ROOT "build\_rthooks"
    $rthPath = Join-Path $rthDir "rthook_build_config.py"
    if (-not (Test-Path -LiteralPath $rthDir)) { New-Item -ItemType Directory -Path $rthDir -Force | Out-Null }

    # Safely quote PCName as a Python string literal
    # (escape single quotes by doubling them)
    $quotedPCName = "'" + ($PCName -replace "'", "''") + "'"

    $rthContent = @"
# Auto-generated. Ensures 'ipat_watchdog.build_config' exists inside the frozen app.
import sys, types
mod = types.ModuleType('ipat_watchdog.build_config')
mod.PC_NAME = $quotedPCName
sys.modules['ipat_watchdog.build_config'] = mod
"@
    Set-Content -Path $rthPath -Value $rthContent -Encoding UTF8
    Write-Host "Runtime hook generated: $rthPath"

    Write-PipelineStep "PYINSTALLER" "Building executable"

    # Build executable using PyInstaller
    # IMPORTANT: The spec named here must exist at build/specs/<PCName>.spec
    $specFile = "build/specs/$CI_JOB_NAME.spec"
    Write-Host "Using spec file: $specFile"

    if (-not (Test-Path $specFile)) {
        Write-PipelineError "PYINSTALLER" "Spec file not found: $specFile" 1
    }

    $env:PYTHONPATH = "$env:PROJECT_ROOT\src"
    $pyArgs = @($specFile, '--clean', '--noconfirm')
    if ($Diagnostics) { $pyArgs += @('--log-level','DEBUG') }

    $pyLogDir = Join-Path $env:PROJECT_ROOT 'build\logs'
    if (-not (Test-Path -LiteralPath $pyLogDir)) { New-Item -ItemType Directory -Path $pyLogDir -Force | Out-Null }
    $pyLog = Join-Path $pyLogDir ("pyinstaller-{0}-{1:yyyyMMdd-HHmmss}.log" -f $CI_JOB_NAME,(Get-Date))

    Write-Host ("PyInstaller command: {0} -m PyInstaller {1}" -f $venv.Python, ($pyArgs -join ' '))
    & $venv.Python -m PyInstaller @pyArgs 2>&1 | Tee-Object -FilePath $pyLog

    if ($LASTEXITCODE -ne 0) {
        Write-Host ("Last 200 lines of {0}:" -f $pyLog) -ForegroundColor Yellow
        Get-Content -Path $pyLog -Tail 200 | Write-Host
        Write-PipelineError "PYINSTALLER" "PyInstaller failed with exit code $LASTEXITCODE (see $pyLog)" $LASTEXITCODE
    }

    Write-PipelineStep "VALIDATION" "Checking build output"

    # Verify build results
    $artifacts = Test-BuildArtifacts -ProjectRoot $env:PROJECT_ROOT -JobName $CI_JOB_NAME
    Write-Host "Build succeeded. Executable: $($artifacts.BinaryPath)" -ForegroundColor Green

    # Display build info
    $fileInfo = Get-Item $artifacts.BinaryPath
    Write-Host "File size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB"
    Write-Host "Created: $($fileInfo.CreationTime)"

} catch {
    Write-Host "Verbose error details:" -ForegroundColor Red
    $_ | Format-List * | Out-String | Write-Host
    if ($_.InvocationInfo) { Write-Host "At: $($_.InvocationInfo.PositionMessage)" }
    Write-DiagnosticSnapshot -Title "Build Failure Snapshot"
    Write-PipelineError "BUILD" "Build failed: $($_.Exception.Message)" 1
} finally {
    # Clean up generated build_config.py to avoid accidental commits
    try {
        if ($buildConfigPath -and (Test-Path -LiteralPath $buildConfigPath)) {
            Remove-Item -LiteralPath $buildConfigPath -Force -ErrorAction SilentlyContinue
        }
    } catch {}
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nBuild pipeline completed successfully." -ForegroundColor Green
