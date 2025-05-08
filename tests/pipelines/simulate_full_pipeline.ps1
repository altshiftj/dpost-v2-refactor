# simulate_full_pipeline.ps1

. "$PSScriptRoot\env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")
$ErrorActionPreference = 'Stop'

Write-Host 'Running full pipeline simulation...'

$healthPassed = $false

    & "$PSScriptRoot\simulate_test.ps1"
    & "$PSScriptRoot\simulate_build.ps1"
    & "$PSScriptRoot\simulate_sign.ps1"
    & "$PSScriptRoot\simulate_deploy.ps1"
    
try {
    & "$PSScriptRoot\simulate_run.ps1"

    & "$PSScriptRoot\simulate_health.ps1"
    if ($LASTEXITCODE -eq 0) {
        $healthPassed = $true
        Write-Host 'Service is healthy.'
    } else {
        Write-Warning 'Health check failed.'
    }
}
finally {
    if (-not $healthPassed) {
        Write-Host 'Running rollback...'
        & "$PSScriptRoot\simulate_rollback.ps1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'Rollback completed.'
        } else {
            Write-Error 'Rollback failed.'
        }
        exit 1
    }
}

Write-Host 'Pipeline simulation completed successfully.'
