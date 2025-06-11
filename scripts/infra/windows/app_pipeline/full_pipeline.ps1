# simulate_full_pipeline.ps1

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../../../..")
$ErrorActionPreference = 'Stop'

Write-Host 'Running full pipeline simulation...'

$healthPassed = $false

    & "$PSScriptRoot\01-test.ps1"
    & "$PSScriptRoot\02-build.ps1"
    & "$PSScriptRoot\03-sign.ps1"
    & "$PSScriptRoot\04-deploy.ps1"

try {
    & "$PSScriptRoot\05-run.ps1"

    & "$PSScriptRoot\06-health_check.ps1"
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
        & "$PSScriptRoot\07-rollback.ps1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'Rollback completed.'
        } else {
            Write-Error 'Rollback failed.'
        }
        exit 1
    }
}

Write-Host 'Pipeline simulation completed successfully.'
