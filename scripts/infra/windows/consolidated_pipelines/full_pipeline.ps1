<# ========================= full_pipeline.ps1 =========================
Purpose:
- Unified pipeline orchestrator for all access configurations
- Runs complete pipeline: test -> build -> sign -> deploy -> run -> health_check
- Supports all access methods with proper error handling
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    
    [Parameter(Mandatory = $false)]
    [string] $PCName = "",
    
    [Parameter(Mandatory = $false)]
    [string[]] $Steps = @("test", "build", "sign", "deploy", "run", "health_check"),
    
    [Parameter(Mandatory = $false)]
    [switch] $ContinueOnError,
    
    [Parameter(Mandatory = $false)]
    [switch] $SkipConfirmation,
    
    [Parameter(Mandatory = $false)]
    [switch] $ListPCs
)

# Load utilities
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"

# Handle special flags first
if ($ListPCs) {
    Write-Host "Available PC Configurations:" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    $availablePCs = Get-AvailablePCs
    foreach ($pc in $availablePCs) {
        $pcConfigs = Get-PCConfigurations
        $pcConfig = $pcConfigs[$pc]
        Write-Host "  $pc" -ForegroundColor Green
        Write-Host "    Method: $($pcConfig.Method)" -ForegroundColor Gray
        Write-Host "    PC Name: $($pcConfig.PCName)" -ForegroundColor Gray
        if ($pcConfig.TargetIP) {
            Write-Host "    Target IP: $($pcConfig.TargetIP)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    exit 0
}

# Handle PC name parameter
$finalAccessConfig = $AccessConfig
if ($PCName -ne "") {
    # User specified a PC name, check if it exists in our configurations
    $availablePCs = Get-AvailablePCs
    if ($availablePCs -contains $PCName) {
        $finalAccessConfig = $PCName
        Write-Host "Using PC configuration: $PCName" -ForegroundColor Green
    } else {
        Write-Host "ERROR: PC '$PCName' not found in configurations" -ForegroundColor Red
        Write-Host "Available PCs: $($availablePCs -join ', ')" -ForegroundColor Yellow
        Write-Host "Use -ListPCs to see detailed information" -ForegroundColor Yellow
        exit 1
    }
}

$overallTimer = Start-PipelineTimer
$completedSteps = @()
$failedStep = $null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   IPAT Watchdog - Full Pipeline       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Access Config: $finalAccessConfig"
if ($PCName -ne "" -and $finalAccessConfig -eq $PCName) {
    Write-Host "PC Name: $PCName (resolved from configuration)"
}
Write-Host "Steps: $($Steps -join ' -> ')"
Write-Host "Continue on Error: $ContinueOnError"
Write-Host ""

# Confirmation prompt (unless skipped)
if (-not $SkipConfirmation) {
    $confirmation = Read-Host "Proceed with pipeline execution? (y/N)"
    if ($confirmation -notmatch '^[Yy]') {
        Write-Host "Pipeline cancelled by user" -ForegroundColor Yellow
        exit 0
    }
}

try {
    foreach ($step in $Steps) {
        $stepNumber = $Steps.IndexOf($step) + 1
        $totalSteps = $Steps.Count
        
        Write-Host "`n" + ("=" * 60) -ForegroundColor Green
        Write-Host "STEP $stepNumber/$totalSteps`: $($step.ToUpper())" -ForegroundColor Green
        Write-Host ("=" * 60) -ForegroundColor Green
        
        $stepTimer = Start-PipelineTimer
        $stepSuccess = $false
        
        try {
            switch ($step.ToLower()) {
                "test" {
                    & "$PSScriptRoot\01-test.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "build" {
                    & "$PSScriptRoot\02-build.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "sign" {
                    & "$PSScriptRoot\03-sign.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "deploy" {
                    & "$PSScriptRoot\04-deploy.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "run" {
                    & "$PSScriptRoot\05-run.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "health_check" {
                    & "$PSScriptRoot\06-health_check.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                "rollback" {
                    & "$PSScriptRoot\07-rollback.ps1" -AccessConfig $finalAccessConfig
                    $stepSuccess = $LASTEXITCODE -eq 0
                }
                
                default {
                    Write-Error "Unknown pipeline step: $step"
                    $stepSuccess = $false
                }
            }
            
        } catch {
            Write-Error "Step '$step' failed with exception: $($_.Exception.Message)"
            $stepSuccess = $false
        }
        
        $stepDuration = Stop-PipelineTimer $stepTimer
        
        if ($stepSuccess) {
            $completedSteps += $step
            Write-Host "`nSTEP $stepNumber COMPLETED: $step" -ForegroundColor Green
            Write-Host "Duration: $($stepDuration.ToString('hh\:mm\:ss'))" -ForegroundColor Green
        } else {
            $failedStep = $step
            Write-Host "`nSTEP $stepNumber FAILED: $step" -ForegroundColor Red
            Write-Host "Duration: $($stepDuration.ToString('hh\:mm\:ss'))" -ForegroundColor Red
            
            if (-not $ContinueOnError) {
                throw "Pipeline stopped due to step failure: $step"
            } else {
                Write-Warning "Continuing pipeline despite step failure (ContinueOnError = true)"
            }
        }
    }
    
} catch {
    Write-Host "`n" + ("!" * 60) -ForegroundColor Red
    Write-Host "PIPELINE FAILED" -ForegroundColor Red
    Write-Host ("!" * 60) -ForegroundColor Red
    Write-Error $_.Exception.Message
    
    # Suggest rollback if we got past deployment
    if ($completedSteps -contains "deploy" -and $failedStep -ne "rollback") {
        Write-Host "`nSuggested recovery action:" -ForegroundColor Yellow
        Write-Host ".\07-rollback.ps1 -AccessConfig $AccessConfig"
    }
    
    exit 1
}

# Final summary
$overallDuration = Stop-PipelineTimer $overallTimer

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "PIPELINE COMPLETED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "Access Configuration: $AccessConfig"
Write-Host "Completed Steps: $($completedSteps -join ', ')"
Write-Host "Total Duration: $($overallDuration.ToString('hh\:mm\:ss'))"

if ($failedStep) {
    Write-Host "Failed Step: $failedStep (continued due to ContinueOnError)" -ForegroundColor Yellow
}

Write-Host "`nPipeline Summary:" -ForegroundColor Green
foreach ($step in $Steps) {
    $status = if ($completedSteps -contains $step) { "[PASS]" } else { "[FAIL]" }
    $color = if ($completedSteps -contains $step) { "Green" } else { "Red" }
    Write-Host "  $status $step" -ForegroundColor $color
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Verify application is running correctly"
Write-Host "  2. Monitor application logs"
Write-Host "  3. Test critical functionality"
Write-Host "  4. Run health checks periodically"

exit 0
