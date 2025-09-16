<# ========================= access-configs.ps1 =========================
Purpose:
- Access method configurations for different target environments
- Supports local, direct SSH, and router tunnel access patterns
- Environment-specific connection parameters
================================================================ #>

# ------------------------------
# Access Configuration Functions (PowerShell 5 Compatible)
# ------------------------------
function New-AccessConfig {
    param(
        [string] $Method,
        [string] $TargetIP = "",
        [string] $TargetUser = "",
        [string] $SSHPort = "22"
    )
    
    return @{
        Method = $Method
        TargetIP = $TargetIP
        TargetUser = $TargetUser
        SSHPort = $SSHPort
        SecurePaths = @{}
        CustomProperties = @{}
    }
}

function New-LocalAccessConfig {
    $config = New-AccessConfig -Method "local" -TargetIP "127.0.0.1" -TargetUser $env:USERNAME
    return $config
}

function New-DirectSSHConfig {
    param(
        [string] $TargetIP,
        [string] $TargetUser
    )
    
    $config = New-AccessConfig -Method "direct" -TargetIP $TargetIP -TargetUser $TargetUser
    return $config
}

function New-RouterTunnelConfig {
    param(
        [string] $RouterIP,
        [string] $RouterUser,
        [string] $TargetIP,
        [string] $TargetUser
    )
    
    $config = New-AccessConfig -Method "router" -TargetIP $TargetIP -TargetUser $TargetUser
    $config.RouterIP = $RouterIP
    $config.RouterUser = $RouterUser
    $config.RouterSSHKey = ""
    $config.RouterHostKey = ""
    $config.TargetSSHKey = ""
    $config.TargetHostKey = ""
    $config.TunnelPort = "2222"
    return $config
}

# ------------------------------
# PC Configuration Database
# ------------------------------
function Get-PCConfigurations {
    return @{
        # Legacy configurations (for backward compatibility)
        "admin" = @{
            Method = "direct"
            TargetIP = "134.169.58.85"
            TargetUser = "TischREM"
            SSHPort = "22"
            PCName = "tischrem_blb"
            Devices = @("sem_phenomxl2")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                TargetPass = "$env:USERPROFILE\.secure\tischrem_blb.txt"
            }
            SSHHostKey = 'AAAAC3NzaC1lZDI1NTE5AAAAID/Hjy2IPejhgLVP20MPFUGjiSBaBSAPdSuC2jZDKcv4'
            TunnelPorts = @(8000, 8001)
        }
        
        "router_admin" = @{
            Method = "router"
            RouterIP = "144.169.58.132"
            RouterUser = "jamfitz"
            TargetIP = "192.168.1.99"
            TargetUser = "horiba"
            SSHPort = "22"
            PCName = "horiba_blb"
            Devices = @("psa_horiba", "dsv_horiba")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                RouterPass = "$env:USERPROFILE\.secure\misch_route.txt"
                TargetPass = "$env:USERPROFILE\.secure\horiba_blb.txt"
            }
            RouterSSHKey = "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk"
            TargetSSHKey = "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk"
            RouterHostKey = 'SHA256:uj6kBrFxe0qWj9SC3avJ5PTPCstPJ/Cp33v/VtiiWEk'
            TargetHostKey = 'SHA256:e1Aj6OvJNCXlNPv/asJo/jnuFKLkjEObTDi38g73Nt8'
            TunnelPort = "2222"
        }
        
        "sub_admin" = @{
            Method = "direct"
            TargetIP = "134.169.58.131"
            TargetUser = "messrechner"
            SSHPort = "22"
            PCName = "utm_zwick"
            Devices = @("utm_zwick")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                TargetPass = "$env:USERPROFILE\.secure\utm_zwick.txt"
            }
            TunnelPorts = @(8000, 8001)
        }
        
        "local" = @{
            Method = "local"
            TargetIP = "127.0.0.1"
            TargetUser = $env:USERNAME
            SSHPort = "22"
            PCName = "tischrem_blb"
            Devices = @("test_device")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
            }
        }
        
        # New PC configurations - add your PCs here
        "tischrem_blb" = @{
            Method = "direct"
            TargetIP = "134.169.58.85"
            TargetUser = "TischREM"
            SSHPort = "22"
            PCName = "tischrem_blb"
            Devices = @("sem_phenomxl2")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                TargetPass = "$env:USERPROFILE\.secure\tischrem_blb.txt"
            }
            SSHHostKey = 'AAAAC3NzaC1lZDI1NTE5AAAAID/Hjy2IPejhgLVP20MPFUGjiSBaBSAPdSuC2jZDKcv4'
        }
        
        "horiba_blb" = @{
            Method = "router"
            RouterIP = "134.169.58.199"
            RouterUser = "jamfitz"
            TargetIP = "192.168.1.2"
            TargetUser = "horiba"
            SSHPort = "22"
            PCName = "horiba_blb"
            Devices = @("psa_horiba", "dsv_horiba")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                RouterPass = "$env:USERPROFILE\.secure\misch_route.txt"
                TargetPass = "$env:USERPROFILE\.secure\horiba_blb.txt"
            }
            RouterSSHKey = "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk"
            TargetSSHKey = "C:\Users\fitz\.ssh\id_rsa_jamfitz_ppk.ppk"
            RouterHostKey = 'SHA256:uj6kBrFxe0qWj9SC3avJ5PTPCstPJ/Cp33v/VtiiWEk'
            TargetHostKey = 'SHA256:e1Aj6OvJNCXlNPv/asJo/jnuFKLkjEObTDi38g73Nt8'
            TunnelPort = "2222"
        }
        
        "zwick_blb" = @{
            Method = "direct"
            TargetIP = "134.169.58.118"
            TargetUser = "messrechner"
            SSHPort = "22"
            PCName = "zwick_blb"
            Devices = @("utm_zwick")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                TargetPass = "$env:USERPROFILE\.secure\zwick_blb.txt"
            }
            SSHHostKey = 'AAAAC3NzaC1lZDI1NTE5AAAAIEaXU0p4npXkadBZ0RSBVFeaMg3HtUmErmEJo7kj+gR9'
        }
        
        "lab-workstation" = @{
            Method = "direct"
            TargetIP = "192.168.1.100"
            TargetUser = "LabUser"
            PCName = "lab_workstation_blb"
            Devices = @("test_device")
            SecurePaths = @{
                PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
                PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
                TargetPass = "$env:USERPROFILE\.secure\lab_workstation.txt"
            }
            SSHHostKey = 'ssh-rsa AAAAB3NzaC1yc2EAAAAB...'  # Replace with actual key
        }
    }
}

# List available PC configurations
function Get-AvailablePCs {
    $pcConfigs = Get-PCConfigurations
    return $pcConfigs.Keys | Sort-Object
}

function Get-PCDevices {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PCName
    )
    $pcConfigs = Get-PCConfigurations
    if (-not $pcConfigs.ContainsKey($PCName)) {
        $available = ($pcConfigs.Keys | Sort-Object) -join "', '"
        throw "PC '$PCName' not found. Available PCs: '$available'"
    }
    $devices = @()
    if ($pcConfigs[$PCName].Devices) {
        $devices = @($pcConfigs[$PCName].Devices)
    }
    return $devices
}

# Backward-compatible wrapper used by other scripts
function Get-DevicesForPC {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PCName,
        [string] $ProjectRoot = $null
    )
    return Get-PCDevices -PCName $PCName
}
function Get-AccessConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ConfigName
    )
    
    $pcConfigs = Get-PCConfigurations
    
    if ($pcConfigs.ContainsKey($ConfigName)) {
        $pcConfig = $pcConfigs[$ConfigName]
        
        # Convert PC configuration to standardized access config format
        switch ($pcConfig.Method.ToLower()) {
            "local" {
                $config = New-LocalAccessConfig
                $config.SecurePaths = $pcConfig.SecurePaths
                $config.CustomProperties = @{
                    PCName = $pcConfig.PCName
                }
                return $config
            }
            
            "direct" {
                $config = New-DirectSSHConfig -TargetIP $pcConfig.TargetIP -TargetUser $pcConfig.TargetUser
                $config.SSHPort = if ($pcConfig.SSHPort) { $pcConfig.SSHPort } else { "22" }
                $config.SecurePaths = $pcConfig.SecurePaths
                # Build CustomProperties carefully to avoid missing property errors
                $custom = @{ PCName = $pcConfig.PCName }
                if ($pcConfig.ContainsKey('SSHHostKey') -and $pcConfig.SSHHostKey) { $custom.SSHHostKey = $pcConfig.SSHHostKey }
                if ($pcConfig.ContainsKey('TunnelPorts') -and $pcConfig.TunnelPorts) { $custom.TunnelPorts = $pcConfig.TunnelPorts }
                $config.CustomProperties = $custom
                return $config
            }
            
            "router" {
                $config = New-RouterTunnelConfig -RouterIP $pcConfig.RouterIP -RouterUser $pcConfig.RouterUser -TargetIP $pcConfig.TargetIP -TargetUser $pcConfig.TargetUser
                $config.SSHPort = if ($pcConfig.SSHPort) { $pcConfig.SSHPort } else { "22" }
                $config.RouterSSHKey = $pcConfig.RouterSSHKey
                $config.TargetSSHKey = $pcConfig.TargetSSHKey
                $config.RouterHostKey = $pcConfig.RouterHostKey
                $config.TargetHostKey = $pcConfig.TargetHostKey
                $config.TunnelPort = if ($pcConfig.TunnelPort) { $pcConfig.TunnelPort } else { "2222" }
                $config.SecurePaths = $pcConfig.SecurePaths
                $config.CustomProperties = @{
                    PCName = $pcConfig.PCName
                }
                return $config
            }
            
            default {
                throw "Unknown access method '$($pcConfig.Method)' for PC '$ConfigName'"
            }
        }
    }
    
    # Show available PCs if the requested one doesn't exist
    $availablePCs = Get-AvailablePCs
    $availableList = $availablePCs -join "', '"
    throw "PC configuration '$ConfigName' not found. Available PCs: '$availableList'"
}

# ------------------------------
# Environment Setup
# ------------------------------
function Initialize-PipelineEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string] $AccessConfigName,
        [string] $ProjectRoot = $null
    )
    
    # Get project root
    if (-not $ProjectRoot) {
        $needDetect = $true
        if ($env:PROJECT_ROOT) {
            $pp = Join-Path $env:PROJECT_ROOT 'pyproject.toml'
            if ((Test-Path -LiteralPath $env:PROJECT_ROOT) -and (Test-Path -LiteralPath $pp)) {
                $ProjectRoot = $env:PROJECT_ROOT
                $needDetect = $false
            } else {
                Write-Warning "Ignoring preset PROJECT_ROOT '$($env:PROJECT_ROOT)' (no pyproject.toml found there)."
            }
        }
        
        if ($needDetect) {
            $ProjectRoot = Get-ProjectRoot
        }
    }
    
    $env:PROJECT_ROOT = $ProjectRoot
    Write-Host "Project Root: $ProjectRoot"
    
    # Get access configuration
    $accessConfig = Get-AccessConfig -ConfigName $AccessConfigName
    
    # Set environment variables from configuration
    $env:CI_JOB_NAME = $accessConfig.CustomProperties.PCName
    $env:PC_NAME = $env:CI_JOB_NAME  # Set for the application to use
    $env:TARGET_IP = $accessConfig.TargetIP
    $env:TARGET_USER = $accessConfig.TargetUser
    $env:SSH_PORT = $accessConfig.SSHPort
    
    # Load Git metadata
    $gitData = Get-GitMetadata
    if ($gitData.Success) {
        $env:COMMIT_TAG = $gitData.CommitTag
        $env:GIT_BRANCH = $gitData.Branch
        $env:COMMIT_HASH = $gitData.CommitHash
        $env:BUILD_TIME = $gitData.BuildTime
    }
    
    # Load secure passwords
    $env:SIGNING_CERT_PFX = $accessConfig.SecurePaths.PFX
    if ($accessConfig.SecurePaths.PFXPass) {
        $env:SIGNING_CERT_PASS = Get-SecurePassword -PasswordFilePath $accessConfig.SecurePaths.PFXPass -Description "PFX password"
    }
    if ($accessConfig.SecurePaths.TargetPass) {
        $env:TARGET_PASS = Get-SecurePassword -PasswordFilePath $accessConfig.SecurePaths.TargetPass -Description "Target password"
    }
    
    # Router-specific configuration
    if ($accessConfig.Method -eq "router") {
        $env:ROUTER_IP = $accessConfig.RouterIP
        $env:ROUTER_USER = $accessConfig.RouterUser
        $env:ROUTER_SSH_KEY = $accessConfig.RouterSSHKey
        $env:ROUTER_SSH_HOSTKEY = $accessConfig.RouterHostKey
        $env:TARGET_SSH_KEY = $accessConfig.TargetSSHKey
        $env:TARGET_SSH_HOSTKEY = $accessConfig.TargetHostKey
        $env:TARGET_TUNNEL_PORT = $accessConfig.TunnelPort
        
        if ($accessConfig.SecurePaths.RouterPass) {
            $env:ROUTER_PASS = Get-SecurePassword -PasswordFilePath $accessConfig.SecurePaths.RouterPass -Description "Router password"
        }
    }
    
    # Set derived paths
    $env:REMOTE_PATH = "C:\Watchdog"
    $env:REMOTE_EXE = "$env:REMOTE_PATH\wd-$env:CI_JOB_NAME.exe"
    
    # Custom properties
    if ($accessConfig.CustomProperties.SSHHostKey) {
        $env:SSH_HOSTKEY = $accessConfig.CustomProperties.SSHHostKey
    }
    if ($accessConfig.CustomProperties -and ($accessConfig.CustomProperties.ContainsKey('TunnelPorts')) -and $accessConfig.CustomProperties.TunnelPorts) {
        $env:TUN_PORT_0 = $accessConfig.CustomProperties.TunnelPorts[0]
        $env:TUN_PORT_1 = $accessConfig.CustomProperties.TunnelPorts[1]
    }
    
    # Export device list for this PC (comma-separated)
    try {
        $pcDevices = Get-PCDevices -PCName $env:CI_JOB_NAME
        $env:PC_DEVICES = ($pcDevices -join ',')
    } catch {
        $env:PC_DEVICES = ""
    }

    Write-Host "Environment initialized for: $AccessConfigName"
    Write-Host "CI_JOB_NAME: $env:CI_JOB_NAME"
    Write-Host "TARGET: $env:TARGET_USER@$env:TARGET_IP"
    Write-Host "ACCESS_METHOD: $($accessConfig.Method)"
    if ($env:PC_DEVICES) { Write-Host "DEVICES: $env:PC_DEVICES" }
    
    return $accessConfig
}
