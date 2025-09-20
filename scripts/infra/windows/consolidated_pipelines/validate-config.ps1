<# ========================= validate-config.ps1 =========================
Purpose:
- Validates access configuration setup
- Checks required files, tools, and connectivity
- Provides setup guidance and troubleshooting
================================================================ #>

param(
    [Parameter(Mandatory = $false)]
    [string] $AccessConfig = "admin",
    
    [Parameter(Mandatory = $false)]
    [string] $PCName = "",
    
    [Parameter(Mandatory = $false)]
    [switch] $TestConnectivity,
    
    [Parameter(Mandatory = $false)]
    [switch] $ValidateAllPCs
)

# Load utilities and configurations
. "$PSScriptRoot\pipeline-utils.ps1"
. "$PSScriptRoot\access-configs.ps1"

# Handle PC-specific validation modes
if ($ValidateAllPCs) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   PC Configuration Validation         " -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    $availablePCs = Get-AvailablePCs
    $successCount = 0
    $errorCount = 0
    
    foreach ($pc in $availablePCs) {
        try {
            $config = Get-AccessConfig -ConfigName $pc
            Write-Host "✓ $pc" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "✗ $pc`: $($_.Exception.Message)" -ForegroundColor Red
            $errorCount++
        }
    }
    
    Write-Host ""
    Write-Host "Validation Summary:" -ForegroundColor Cyan
    Write-Host "  Total PCs: $($availablePCs.Count)" -ForegroundColor Gray
    Write-Host "  Successful: $successCount" -ForegroundColor Green
    Write-Host "  Errors: $errorCount" -ForegroundColor Red
    
    exit ($errorCount -eq 0 ? 0 : 1)
}

if ($PCName -ne "") {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   PC Configuration Validation         " -ForegroundColor Cyan  
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Validating PC: $PCName" -ForegroundColor Yellow
    
    try {
        $config = Get-AccessConfig -ConfigName $PCName
        Write-Host "✓ PC '$PCName' configuration loaded successfully" -ForegroundColor Green
        Write-Host "  Method: $($config.Method)" -ForegroundColor Gray
        Write-Host "  PC Name: $($config.CustomProperties.PCName)" -ForegroundColor Gray
        
        if ($config.TargetIP) {
            Write-Host "  Target: $($config.TargetUser)@$($config.TargetIP):$($config.SSHPort)" -ForegroundColor Gray
        }
        
        if ($config.RouterIP) {
            Write-Host "  Router: $($config.RouterUser)@$($config.RouterIP)" -ForegroundColor Gray
            Write-Host "  Tunnel Port: $($config.TunnelPort)" -ForegroundColor Gray
        }
        
        # Set AccessConfig to the resolved PC name for remaining validation
        $AccessConfig = $PCName
        
    } catch {
        Write-Host "✗ Error loading PC '$PCName': $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Configuration Validation Tool       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$validationResults = @()

function Add-ValidationResult {
    param(
        [string] $Component,
        [string] $Status,
        [string] $Message,
        [string] $Recommendation = ""
    )
    
    $validationResults += @{
        Component = $Component
        Status = $Status
        Message = $Message
        Recommendation = $Recommendation
    }
    
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    
    Write-Host "[$Status] $Component`: $Message" -ForegroundColor $color
    if ($Recommendation) {
        Write-Host "    → $Recommendation" -ForegroundColor Gray
    }
}

Write-Host "Validating access configuration: $AccessConfig`n"

try {
    # 1. Project Root Validation
    Write-Host "1. Project Structure Validation" -ForegroundColor Yellow
    try {
        $projectRoot = Get-ProjectRoot
        Add-ValidationResult "Project Root" "PASS" "Found at: $projectRoot"
        
        # Check key files
        $keyFiles = @("pyproject.toml", "src\ipat_watchdog\pc_device_mapping.py")
        foreach ($file in $keyFiles) {
            $filePath = Join-Path $projectRoot $file
            if (Test-Path $filePath) {
                Add-ValidationResult "File: $file" "PASS" "Found"
            } else {
                Add-ValidationResult "File: $file" "FAIL" "Missing" "Ensure you're running from the correct project directory"
            }
        }
    } catch {
        Add-ValidationResult "Project Root" "FAIL" $_.Exception.Message "Navigate to the project root directory"
    }
    
    # 2. Access Configuration Validation
    Write-Host "`n2. Access Configuration Validation" -ForegroundColor Yellow
    try {
        $config = Get-AccessConfig -ConfigName $AccessConfig
        Add-ValidationResult "Config Load" "PASS" "Successfully loaded $AccessConfig configuration"
        
        # Validate required properties
        if ($config.TargetIP) {
            Add-ValidationResult "Target IP" "PASS" $config.TargetIP
        } else {
            Add-ValidationResult "Target IP" "FAIL" "Not configured"
        }
        
        if ($config.TargetUser) {
            Add-ValidationResult "Target User" "PASS" $config.TargetUser
        } else {
            Add-ValidationResult "Target User" "FAIL" "Not configured"
        }
        
    } catch {
        Add-ValidationResult "Config Load" "FAIL" $_.Exception.Message "Check access-configs.ps1 for configuration definition"
    }
    
    # 3. Security Files Validation
    Write-Host "`n3. Security Files Validation" -ForegroundColor Yellow
    
    # Certificate file
    $pfxPath = "$env:USERPROFILE\.secure\ipat_wd.pfx"
    if (Test-Path $pfxPath) {
        Add-ValidationResult "Signing Certificate" "PASS" "Found at: $pfxPath"
    } else {
        Add-ValidationResult "Signing Certificate" "FAIL" "Missing: $pfxPath" "Place your code signing certificate in the .secure folder"
    }
    
    # Certificate password
    $pfxPassPath = "$env:USERPROFILE\.secure\pfxpass.txt"
    if (Test-Path $pfxPassPath) {
        Add-ValidationResult "Certificate Password" "PASS" "Found (encrypted)"
    } else {
        Add-ValidationResult "Certificate Password" "FAIL" "Missing: $pfxPassPath" "Create encrypted password file using ConvertTo-SecureString"
    }
    
    # PC-specific password
    if ($config.CustomProperties.PCName) {
        $pcPassPath = "$env:USERPROFILE\.secure\$($config.CustomProperties.PCName).txt"
        if (Test-Path $pcPassPath) {
            Add-ValidationResult "PC Password" "PASS" "Found for $($config.CustomProperties.PCName)"
        } else {
            Add-ValidationResult "PC Password" "FAIL" "Missing: $pcPassPath" "Create encrypted password file for target PC"
        }
    }
    
    # Router-specific files (for router_admin)
    if ($config.Method -eq "router") {
        $routerPassPath = "$env:USERPROFILE\.secure\misch_route.txt"
        if (Test-Path $routerPassPath) {
            Add-ValidationResult "Router Password" "PASS" "Found"
        } else {
            Add-ValidationResult "Router Password" "FAIL" "Missing: $routerPassPath" "Create encrypted password file for router"
        }
        
        if ($config.RouterSSHKey -and (Test-Path $config.RouterSSHKey)) {
            Add-ValidationResult "Router SSH Key" "PASS" "Found: $($config.RouterSSHKey)"
        } else {
            Add-ValidationResult "Router SSH Key" "FAIL" "Missing: $($config.RouterSSHKey)" "Place SSH private key file"
        }
        
        if ($config.TargetSSHKey -and (Test-Path $config.TargetSSHKey)) {
            Add-ValidationResult "Target SSH Key" "PASS" "Found: $($config.TargetSSHKey)"
        } else {
            Add-ValidationResult "Target SSH Key" "FAIL" "Missing: $($config.TargetSSHKey)" "Place SSH private key file"
        }
    }
    
    # 4. Tool Dependencies Validation
    Write-Host "`n4. Tool Dependencies Validation" -ForegroundColor Yellow
    
    # Python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonVersion = python --version
        Add-ValidationResult "Python" "PASS" $pythonVersion
    } else {
        Add-ValidationResult "Python" "FAIL" "Not found in PATH" "Install Python and ensure it's in PATH"
    }
    
    # Git
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitVersion = git --version
        Add-ValidationResult "Git" "PASS" $gitVersion
    } else {
        Add-ValidationResult "Git" "WARN" "Not found in PATH" "Install Git for version metadata"
    }
    
    # PyInstaller (will be installed during build)
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($pythonPath) {
        $pipList = & python -m pip list 2>$null
        if ($pipList -like "*pyinstaller*") {
            Add-ValidationResult "PyInstaller" "PASS" "Available"
        } else {
            Add-ValidationResult "PyInstaller" "WARN" "Not installed" "Will be installed during build step"
        }
    }
    
    # Code signing tool
    if (Get-Command signtool -ErrorAction SilentlyContinue) {
        Add-ValidationResult "SignTool" "PASS" "Available"
    } else {
        Add-ValidationResult "SignTool" "WARN" "Not found in PATH" "Install Windows SDK or Visual Studio Build Tools"
    }
    
    # SSH tools (for non-local access)
    if ($config.Method -ne "local") {
        if (Get-Command plink -ErrorAction SilentlyContinue) {
            Add-ValidationResult "PLink" "PASS" "Available"
        } else {
            Add-ValidationResult "PLink" "FAIL" "Not found in PATH" "Install PuTTY tools and add to PATH"
        }
        
        if (Get-Command pscp -ErrorAction SilentlyContinue) {
            Add-ValidationResult "PSCP" "PASS" "Available"
        } else {
            Add-ValidationResult "PSCP" "FAIL" "Not found in PATH" "Install PuTTY tools and add to PATH"
        }
    }
    
    # 5. Connectivity Testing (if requested)
    if ($TestConnectivity -and $config.Method -ne "local") {
        Write-Host "`n5. Connectivity Testing" -ForegroundColor Yellow
        
        # Import deploy helpers for connection testing
        . "$PSScriptRoot\deploy-helpers.ps1"
        
        if ($config -and $config.Method -eq "direct") {
            $sshConfig = @{
                Host = $config.TargetIP
                Port = $config.SSHPort
                User = $config.TargetUser
                HostKey = $config.CustomProperties.SSHHostKey
            }
            
            if (Test-SSHConnection -Config $sshConfig) {
                Add-ValidationResult "SSH Connectivity" "PASS" "Successfully connected to $($config.TargetIP)"
            } else {
                Add-ValidationResult "SSH Connectivity" "FAIL" "Cannot connect to $($config.TargetIP)" "Check network connectivity, credentials, and SSH service"
            }
        }
        
        if ($config -and $config.Method -eq "router") {
            $routerConfig = @{
                Host = $config.RouterIP
                User = $config.RouterUser
                KeyFile = $config.RouterSSHKey
                HostKey = $config.RouterHostKey
            }
            
            if (Test-SSHConnection -Config $routerConfig) {
                Add-ValidationResult "Router Connectivity" "PASS" "Successfully connected to router"
            } else {
                Add-ValidationResult "Router Connectivity" "FAIL" "Cannot connect to router" "Check router connectivity and SSH configuration"
            }
        }
    }
    
    # 6. Summary and Recommendations
    Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
    Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    
    $passCount = ($validationResults | Where-Object { $_.Status -eq "PASS" }).Count
    $failCount = ($validationResults | Where-Object { $_.Status -eq "FAIL" }).Count
    $warnCount = ($validationResults | Where-Object { $_.Status -eq "WARN" }).Count
    $totalCount = $validationResults.Count
    
    Write-Host "Results: $passCount PASS, $failCount FAIL, $warnCount WARN (Total: $totalCount)" -ForegroundColor White
    
    if ($failCount -eq 0) {
        Write-Host "`nConfiguration is ready for pipeline execution!" -ForegroundColor Green
        Write-Host "You can now run: .\full_pipeline.ps1 -AccessConfig $AccessConfig"
    } else {
        Write-Host "`nConfiguration needs attention before pipeline execution." -ForegroundColor Red
        Write-Host "Please address the FAIL items above before proceeding."
    }
    
    if ($warnCount -gt 0) {
        Write-Host "`nWarning items may affect some pipeline steps but won't prevent execution." -ForegroundColor Yellow
    }
    
    # Detailed recommendations
    $failedItems = $validationResults | Where-Object { $_.Status -eq "FAIL" -and $_.Recommendation }
    if ($failedItems) {
        Write-Host "`nRequired Actions:" -ForegroundColor Red
        foreach ($item in $failedItems) {
            Write-Host "  • $($item.Component): $($item.Recommendation)" -ForegroundColor Gray
        }
    }
    
    $warnItems = $validationResults | Where-Object { $_.Status -eq "WARN" -and $_.Recommendation }
    if ($warnItems) {
        Write-Host "`nOptional Improvements:" -ForegroundColor Yellow
        foreach ($item in $warnItems) {
            Write-Host "  • $($item.Component): $($item.Recommendation)" -ForegroundColor Gray
        }
    }
    
} catch {
    Write-Error "Validation failed: $($_.Exception.Message)"
    exit 1
}

exit $(if ($failCount -eq 0) { 0 } else { 1 })
