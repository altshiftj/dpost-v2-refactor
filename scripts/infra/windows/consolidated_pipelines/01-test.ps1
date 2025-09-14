<# ========================= 01-test.ps1 =========================
Purpose:
- Unified testing script for all access configurations
- Sets up virtual environment and runs pytest
- Uses consolidated pipeline utilities
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
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
    
    # Create virtual environment
    $venv = New-PythonVirtualEnv -VenvName ".test_testvenv" -ProjectRoot $env:PROJECT_ROOT
    
    # Install test dependencies
    $extras = @("ci", $env:CI_JOB_NAME)
    $pipTarget = Get-PipInstallTarget -Extras $extras
    Write-Host "Installing project with extras: $pipTarget"
    $pipArgs = @('-m','pip','install','-e', $pipTarget)
    if ($Diagnostics) { $pipArgs += '--verbose' }
    & $venv.Python @pipArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "TEST SETUP" "Failed to install dependencies" $LASTEXITCODE
    }
    
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
    Stop-PipelineTimer $timer
    Disable-PipelineDiagnostics
}

Write-Host "`nTest pipeline completed successfully." -ForegroundColor Green
