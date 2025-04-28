Write-Host "Starting full pipeline simulation..."

# --- TIMER START ---
$startTime = Get-Date

# Always run scripts relative to this script's folder
$pipelineFolder = $PSScriptRoot

& "$pipelineFolder/simulate_build.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed."; exit 1 }

& "$pipelineFolder/simulate_deploy.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Deploy failed."; exit 1 }

& "$pipelineFolder/simulate_run.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Run failed."; exit 1 }

& "$pipelineFolder/simulate_health.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Health check failed."; exit 1 }

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "Full pipeline simulation completed successfully!" -ForegroundColor Green
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration) -ForegroundColor Green
