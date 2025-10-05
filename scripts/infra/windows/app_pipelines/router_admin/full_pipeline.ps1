<#
    Full pipeline for router-based deployment
    Runs all stages in sequence: test -> build -> sign -> deploy -> run -> health_check
#>

param(
    [switch]$SkipTest,
    [switch]$SkipBuild,
    [switch]$SkipSign,
    [switch]$SkipDeploy,
    [switch]$SkipRun,
    [switch]$SkipHealth,
    [switch]$ContinueOnError
)

. "$PSScriptRoot/00-env.ps1"
Set-Location -Path $env:PROJECT_ROOT

$ErrorActionPreference = if ($ContinueOnError) { "Continue" } else { "Stop" }

Write-Host "========================================="
Write-Host "    IPAT Watchdog Router-Based Pipeline"
Write-Host "========================================="
Write-Host "CI Job: $env:CI_JOB_NAME"
Write-Host "Router: $env:ROUTER_IP"
Write-Host "Target: $env:TARGET_IP"
Write-Host "Project: $env:PROJECT_ROOT"
Write-Host "========================================="

$pipelineStart = Get-Date
$stages = @()

function Invoke-Stage {
    param(
        [string]$Name,
        [string]$Script,
        [switch]$Skip
    )
    
    if ($Skip) {
        Write-Host "`nSKIPPING: $Name"
        return @{ Name = $Name; Status = "Skipped"; Duration = "00:00:00" }
    }
    
    Write-Host "`nSTARTING: $Name"
    Write-Host "Script: $Script"
    Write-Host ("Time: {0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date))
    Write-Host ("-" * 50)
    
    $stageStart = Get-Date
    
    try {
        & "$PSScriptRoot/$Script"
        $exitCode = $LASTEXITCODE
        
        $duration = (Get-Date) - $stageStart
        
        if ($exitCode -eq 0) {
            Write-Host ("-" * 50)
            Write-Host ("SUCCESS: $Name (Duration: {0:hh\:mm\:ss})" -f $duration)
            return @{ Name = $Name; Status = "Success"; Duration = $duration.ToString("hh\:mm\:ss"); ExitCode = $exitCode }
        } else {
            Write-Host ("-" * 50)
            Write-Host ("FAILED: $Name (Exit Code: $exitCode, Duration: {0:hh\:mm\:ss})" -f $duration)
            return @{ Name = $Name; Status = "Failed"; Duration = $duration.ToString("hh\:mm\:ss"); ExitCode = $exitCode }
        }
    } catch {
        $duration = (Get-Date) - $stageStart
        Write-Host ("-" * 50)
        Write-Host ("ERROR: $Name - $($_.Exception.Message)")
        Write-Host ("Duration: {0:hh\:mm\:ss}" -f $duration)
        return @{ Name = $Name; Status = "Error"; Duration = $duration.ToString("hh\:mm\:ss"); Error = $_.Exception.Message }
    }
}

# ── PIPELINE STAGES ───────────────────────────────────────────────────

$stages += Invoke-Stage -Name "Test" -Script "01-test.ps1" -Skip:$SkipTest
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Test stage failed. Aborting pipeline."
    exit 1
}

$stages += Invoke-Stage -Name "Build" -Script "02-build.ps1" -Skip:$SkipBuild
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Build stage failed. Aborting pipeline."
    exit 1
}

$stages += Invoke-Stage -Name "Sign" -Script "03-sign.ps1" -Skip:$SkipSign
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Sign stage failed. Aborting pipeline."
    exit 1
}

$stages += Invoke-Stage -Name "Deploy" -Script "04-deploy.ps1" -Skip:$SkipDeploy
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Deploy stage failed. Aborting pipeline."
    exit 1
}

$stages += Invoke-Stage -Name "Run" -Script "05-run.ps1" -Skip:$SkipRun
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Run stage failed. Aborting pipeline."
    exit 1
}

$stages += Invoke-Stage -Name "Health Check" -Script "06-health_check.ps1" -Skip:$SkipHealth
if ($stages[-1].Status -eq "Failed" -and !$ContinueOnError) { 
    Write-Error "Health check failed. Aborting pipeline."
    exit 1
}

# ── PIPELINE SUMMARY ──────────────────────────────────────────────────

$totalDuration = (Get-Date) - $pipelineStart
$successCount = ($stages | Where-Object { $_.Status -eq "Success" }).Count
$failedCount = ($stages | Where-Object { $_.Status -eq "Failed" }).Count
$errorCount = ($stages | Where-Object { $_.Status -eq "Error" }).Count
$skippedCount = ($stages | Where-Object { $_.Status -eq "Skipped" }).Count

Write-Host "`n========================================="
Write-Host "           PIPELINE SUMMARY"
Write-Host "========================================="
Write-Host ("Total Duration: {0:hh\:mm\:ss}" -f $totalDuration)
Write-Host "Stages: $($stages.Count) total"
Write-Host "Success: $successCount"
Write-Host "Failed: $failedCount"
Write-Host "Error: $errorCount"
Write-Host "Skipped: $skippedCount"
Write-Host ""

foreach ($stage in $stages) {
    $icon = switch ($stage.Status) {
        "Success" { "✅" }
        "Failed" { "❌" }
        "Error" { "💥" }
        "Skipped" { "🔄" }
    }
    
    $exitInfo = if ($stage.ExitCode) { " (Exit: $($stage.ExitCode))" } else { "" }
    $errorInfo = if ($stage.Error) { " - $($stage.Error)" } else { "" }
    
    Write-Host ("$icon {0,-15} {1,8} {2}" -f $stage.Name, $stage.Duration, "$exitInfo$errorInfo")
}

Write-Host ""
Write-Host "Target Environment:"
Write-Host "  Router: $env:ROUTER_IP"
Write-Host "  Windows PC: $env:TARGET_IP"
Write-Host "  Job: $env:CI_JOB_NAME"
Write-Host "========================================="

# ── FINAL EXIT CODE ───────────────────────────────────────────────────

$overallSuccess = ($failedCount -eq 0) -and ($errorCount -eq 0)

if ($overallSuccess) {
    Write-Host "PIPELINE COMPLETED SUCCESSFULLY!"
    exit 0
} else {
    Write-Host "PIPELINE COMPLETED WITH ISSUES"
    exit 1
}
