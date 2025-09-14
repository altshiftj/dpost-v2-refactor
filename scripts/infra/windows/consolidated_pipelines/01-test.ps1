<# ========================= 01-test.ps1 =========================
Purpose:
- Unified testing script for all access configurations
- Sets up virtual environment and runs pytest
- Uses consolidated pipeline utilities
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
Write-PipelineStep "INITIALIZE" "Setting up test environment"

Enable-PipelineDiagnostics -Enabled:$Diagnostics -ScriptName "01-test"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    Write-PipelineStep "TEST SETUP" "Creating virtual environment and installing dependencies"
    
    # Resolve PC/Job name for tests
    if (-not $PCName -or [string]::IsNullOrWhiteSpace($PCName)) {
        if ($env:PC_NAME) { $PCName = $env:PC_NAME }
        elseif ($env:CI_JOB_NAME) { $PCName = $env:CI_JOB_NAME }
        else { throw "PCName not provided. Pass -PCName or set PC_NAME/CI_JOB_NAME." }
    }
    $env:PC_NAME = $PCName
    $env:CI_JOB_NAME = $PCName

    # Create virtual environment
    $venv = New-PythonVirtualEnv -VenvName ".test_testvenv" -ProjectRoot $env:PROJECT_ROOT
    
    # Install test dependencies with device and PC-specific extras
    Write-Host "Getting devices for PC: $PCName"
    $devices = Get-DevicesForPC -PCName $PCName -ProjectRoot $env:PROJECT_ROOT
    if ($devices -and $devices.Count -gt 0) {
        Write-Host "Devices for $PCName`: $($devices -join ', ')"
    } else {
        Write-Host "No devices defined for $PCName" -ForegroundColor Yellow
    }
    $allExtras = @('ci') + $devices + @($PCName)
    $pipTarget = Get-PipInstallTarget -Extras $allExtras
    Write-Host "Installing project with extras: $pipTarget"
    $pipArgs = @('-m','pip','install','-e', $pipTarget)
    if ($Diagnostics) { $pipArgs += '--verbose' }
    & $venv.Python @pipArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "TEST SETUP" "Failed to install dependencies" $LASTEXITCODE
    }
    
    # Generate build-time config consumed by the app during tests
    $buildConfigPath = Join-Path $env:PROJECT_ROOT "src\ipat_watchdog\build_config.py"
    $buildConfigContent = @(
        "# Auto-generated for tests. Do not commit.",
        "PC_NAME = '" + $PCName + "'"
    ) -join [Environment]::NewLine
    $null = New-Item -Path (Split-Path $buildConfigPath) -ItemType Directory -Force -ErrorAction SilentlyContinue
    Set-Content -Path $buildConfigPath -Value $buildConfigContent -Encoding UTF8
    
    Write-PipelineStep "PYTEST" "Running test suite"
    
    # Run tests
    & $venv.Python -m pytest tests/ --tb=short --disable-warnings --maxfail=5
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "`nAll tests passed." -ForegroundColor Green
    } else {
        Write-PipelineError "PYTEST" "Tests failed with exit code $exitCode" $exitCode
    }
    
} catch {
    Write-Host "Verbose error details:" -ForegroundColor Red
    $_ | Format-List * | Out-String | Write-Host
    if ($_.InvocationInfo) { Write-Host "At: $($_.InvocationInfo.PositionMessage)" }
    Write-DiagnosticSnapshot -Title "Test Failure Snapshot"
    Write-PipelineError "TEST" "Test execution failed: $($_.Exception.Message)" 1
} finally {
    # Clean up generated build config to avoid accidental commits
    try {
        if ($buildConfigPath -and (Test-Path -LiteralPath $buildConfigPath)) {
            Remove-Item -LiteralPath $buildConfigPath -Force -ErrorAction SilentlyContinue
        }
    } catch {}
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nTest pipeline completed successfully." -ForegroundColor Green
