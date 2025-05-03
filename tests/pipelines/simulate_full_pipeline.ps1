# tests\pipelines\simulate_full_pipeline.ps1
$ErrorActionPreference = 'Stop'

Write-Host 'Running full pipeline simulation...'

& "$PSScriptRoot\simulate_build.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

& "$PSScriptRoot\simulate_sign.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

& "$PSScriptRoot\simulate_deploy.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

& "$PSScriptRoot\simulate_run.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

& "$PSScriptRoot\simulate_health.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Health check failed - running rollback...'
    & "$PSScriptRoot\simulate_rollback.ps1"
    exit 1
}

Write-Host 'Pipeline simulation completed successfully.'
