<# ========================= 02-build.ps1 =========================
Purpose:
- Unified build script for all PC configurations
- Uses PC/device mapping system for dependency resolution
- Creates executable using PyInstaller with PC-specific configuration
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin"
)

# Load utilities and initialize environment
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"

$timer = Start-PipelineTimer
Write-PipelineStep "INITIALIZE" "Setting up build environment"

try {
    $config = Initialize-PipelineEnvironment -AccessConfigName $AccessConfig
    Set-Location -Path $env:PROJECT_ROOT
    
    # Use environment variables or defaults
    $CI_JOB_NAME = $env:CI_JOB_NAME
    $CI_COMMIT_TAG = if ($env:CI_COMMIT_TAG) { $env:CI_COMMIT_TAG } 
                     elseif ($env:COMMIT_TAG) { $env:COMMIT_TAG } 
                     else { "vLocalTest" }
    
    Write-Host "Build Configuration:"
    Write-Host "  Job Name: $CI_JOB_NAME"
    Write-Host "  Commit Tag: $CI_COMMIT_TAG"
    
    Write-PipelineStep "BUILD SETUP" "Creating build environment"
    
    # Create/activate virtual environment
    $venv = New-PythonVirtualEnv -VenvName ".test_buildvenv" -ProjectRoot $env:PROJECT_ROOT
    
    Write-PipelineStep "DEPENDENCIES" "Installing build dependencies"
    
    # Get devices for this PC and install dependencies
    $PC_NAME = $CI_JOB_NAME
    Write-Host "Getting devices for PC: $PC_NAME"
    
    $devices = Get-DevicesForPC -PCName $PC_NAME -ProjectRoot $env:PROJECT_ROOT
    Write-Host "Devices for $PC_NAME`: $($devices -join ', ')"
    
    $deviceExtras = $devices
    $allExtras = @('build') + $deviceExtras + @($PC_NAME)
    
    $pipTarget = Get-PipInstallTarget -Extras $allExtras
    Write-Host "Installing project with extras: $pipTarget"
    & $venv.Python -m pip install -e $pipTarget
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "DEPENDENCIES" "Failed to install build dependencies" $LASTEXITCODE
    }
    
    Write-PipelineStep "VERSION FILE" "Creating version metadata"
    
    # Create version file
    $gitData = @{
        CommitTag = $env:COMMIT_TAG
        CommitHash = $env:COMMIT_HASH
        Branch = $env:GIT_BRANCH
        BuildTime = $env:BUILD_TIME
    }
    
    New-VersionFile -GitData $gitData -OutputPath "version.txt"
    Copy-Item -Force "version.txt" "build/version.txt"
    
    Write-PipelineStep "PYINSTALLER" "Building executable"
    
    # Build executable using PyInstaller
    $specFile = "build/specs/pc_$CI_JOB_NAME.spec"
    Write-Host "Using spec file: $specFile"
    
    if (-not (Test-Path $specFile)) {
        Write-PipelineError "PYINSTALLER" "Spec file not found: $specFile" 1
    }
    
    $env:PYTHONPATH = "$env:PROJECT_ROOT\src"
    pyinstaller $specFile --clean --noconfirm
    
    if ($LASTEXITCODE -ne 0) {
        Write-PipelineError "PYINSTALLER" "PyInstaller failed with exit code $LASTEXITCODE" $LASTEXITCODE
    }
    
    Write-PipelineStep "VALIDATION" "Checking build output"
    
    # Verify build results
    $artifacts = Test-BuildArtifacts -ProjectRoot $env:PROJECT_ROOT -JobName $CI_JOB_NAME
    Write-Host "Build succeeded. Executable: $($artifacts.BinaryPath)" -ForegroundColor Green
    
    # Display build info
    $fileInfo = Get-Item $artifacts.BinaryPath
    Write-Host "File size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB"
    Write-Host "Created: $($fileInfo.CreationTime)"
    
} catch {
    Write-PipelineError "BUILD" "Build failed: $($_.Exception.Message)" 1
} finally {
    Stop-PipelineTimer $timer
}

Write-Host "`nBuild pipeline completed successfully." -ForegroundColor Green
