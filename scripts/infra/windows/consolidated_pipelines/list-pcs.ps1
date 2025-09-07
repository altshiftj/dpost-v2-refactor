<# ========================= list-pcs.ps1 =========================
Purpose:
- Simple utility to list available PC configurations
- Shows PC names, methods, and target information
============================================================== #>

# Load access configurations
. "$PSScriptRoot\access-configs.ps1"

Write-Host "Available PC Configurations:" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

$availablePCs = Get-AvailablePCs
$pcConfigs = Get-PCConfigurations

foreach ($pc in $availablePCs) {
    $pcConfig = $pcConfigs[$pc]
    
    Write-Host "  $pc" -ForegroundColor Green
    Write-Host "    Method: $($pcConfig.Method)" -ForegroundColor Gray
    Write-Host "    PC Name: $($pcConfig.PCName)" -ForegroundColor Gray
    
    if ($pcConfig.TargetIP) {
        Write-Host "    Target IP: $($pcConfig.TargetIP)" -ForegroundColor Gray
        Write-Host "    Target User: $($pcConfig.TargetUser)" -ForegroundColor Gray
    }
    
    if ($pcConfig.RouterIP) {
        Write-Host "    Router IP: $($pcConfig.RouterIP)" -ForegroundColor Gray
        Write-Host "    Router User: $($pcConfig.RouterUser)" -ForegroundColor Gray
    }
    
    Write-Host ""
}

Write-Host "Usage Examples:" -ForegroundColor Yellow
Write-Host "  .\full_pipeline.ps1 -PCName tischrem-pc" -ForegroundColor White
Write-Host "  .\full_pipeline.ps1 -PCName horiba-pc -Steps @('build', 'deploy')" -ForegroundColor White
Write-Host "  .\full_pipeline.ps1 -AccessConfig admin  # Legacy method" -ForegroundColor White
