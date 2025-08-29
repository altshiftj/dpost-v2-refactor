# simulate_full_pipeline.ps1

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../../../..")
$ErrorActionPreference = 'Stop'

Write-Host 'Running full pipeline simulation...'

try {
    & "$PSScriptRoot\01-test.ps1"
    & "$PSScriptRoot\02-build.ps1"
    & "$PSScriptRoot\03-sign.ps1"
    & "$PSScriptRoot\04-deploy.ps1"
} catch {
    Write-Error "Pipeline simulation failed: $_"
    exit 1
}

Write-Host 'Pipeline simulation completed successfully.'

Write-Host 'Now manually run the following commands to log the user out:
ssh adminacct@ip
password
quser
logoff <session_id>'
