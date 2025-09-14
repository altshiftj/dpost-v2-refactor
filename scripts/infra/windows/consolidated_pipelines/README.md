# IPAT Watchdog Consolidated Pipelines

This directory contains the consolidated and refactored pipeline scripts that replace the separate folders (admin, router_admin, sub_admin) with a unified, configurable approach.

**✅ PowerShell 5.0+ Compatible - No Classes, Pure PuTTY Tools Integration**

## Architecture

### Core Components

- **pipeline-utils.ps1**: Shared utilities for all pipeline operations (PowerShell 5 compatible)
- **access-configs.ps1**: Access method configurations using hashtables instead of classes
- **deploy-helpers.ps1**: Deployment-specific functions using PuTTY tools (plink.exe, pscp.exe)

### Pipeline Scripts

1. **01-test.ps1**: Unified testing (runs pytest with proper dependencies)
2. **02-build.ps1**: Unified building (uses PC/device mapping for dependencies)
3. **03-sign.ps1**: Code signing (same for all configurations)
4. **04-deploy.ps1**: Deployment with access method routing
5. **05-run.ps1**: Application startup and service registration
6. **06-health_check.ps1**: Health monitoring and verification
7. **07-rollback.ps1**: Rollback to previous version
8. **full_pipeline.ps1**: Complete pipeline orchestrator

## Access Configurations

### Available Configurations

- **admin**: Direct access or local deployment (default)
- **router_admin**: SSH tunneling through a router to target
- **sub_admin**: Direct SSH access to subnet machines
- **local**: Local development/testing

### Configuration Details

Each access configuration defines:
- Connection parameters (IP, user, ports)
- Authentication methods (passwords, SSH keys)
- Security settings (host keys, certificates)
- PC/device mappings

## PC Configuration System

The consolidated pipeline system includes a PC configuration database that allows you to easily manage multiple target PCs and specify them by name in your pipeline commands.

### Available PC Configurations

Use `.\list-pcs.ps1` or `.\full_pipeline.ps1 -ListPCs` to see all available PC configurations:

- **tischrem-pc** - Direct SSH to TischREM SEM device
- **horiba-pc** - Router tunnel to Horiba test system  
- **zwick-pc** - Direct SSH to Zwick UTM device
- **lab-workstation** - Local development machine
- **admin** - Legacy admin configuration (maps to tischrem-pc)
- **router_admin** - Legacy router configuration (maps to horiba-pc)
- **sub_admin** - Legacy subnet configuration (maps to zwick-pc)
- **local** - Legacy local configuration (maps to lab-workstation)

### Adding New PC Configurations

To add a new PC configuration, edit the `Get-PCConfigurations` function in `access-configs.ps1`:

```powershell
"new-pc" = @{
    Method = "direct"  # or "router" or "local"
    PCName = "new_device_name"
    TargetIP = "192.168.1.100"
    TargetUser = "username"
    SecurePaths = @{
        PFX = "$env:USERPROFILE\.secure\ipat_wd.pfx"
        PFXPass = "$env:USERPROFILE\.secure\pfxpass.txt"
        TargetPass = "$env:USERPROFILE\.secure\new_device.txt"
    }
}
```

## Usage

### Individual Steps

```powershell
# Run specific step with default (admin) configuration
.\01-test.ps1

# Run with specific access configuration
.\02-build.ps1 -AccessConfig "router_admin"
.\04-deploy.ps1 -AccessConfig "sub_admin"

# NEW: Specify PC directly at build time (embeds PC into binary)
.\02-build.ps1 -PCName tischrem_blb

# NEW: Run tests with specific PC/device plugin set
.\01-test.ps1 -PCName tischrem_blb
```

### Full Pipeline

```powershell
# NEW: Using PC Names (Recommended)
# Deploy to TischREM SEM
.\full_pipeline.ps1 -PCName tischrem-pc

# Build and deploy to Horiba system
.\full_pipeline.ps1 -PCName horiba-pc -Steps @('build', 'deploy', 'run')

# Health check on Zwick UTM
.\full_pipeline.ps1 -PCName zwick-pc -Steps @('health_check')

# List all available PCs
.\full_pipeline.ps1 -ListPCs
.\list-pcs.ps1

# LEGACY: Access Config Method (Still Supported)
# Run complete pipeline with admin configuration
.\full_pipeline.ps1 -AccessConfig admin

# Run with specific configuration  
.\full_pipeline.ps1 -AccessConfig router_admin

# Run specific steps only
.\full_pipeline.ps1 -Steps @("build", "deploy", "run")

# Continue on errors (for debugging)
.\full_pipeline.ps1 -ContinueOnError

# Skip confirmation prompt
.\full_pipeline.ps1 -SkipConfirmation
```

### Emergency Rollback

```powershell
# Rollback current deployment
.\07-rollback.ps1

# Force rollback without confirmation
.\07-rollback.ps1 -Force
```

## Key Features

### Unified Codebase
- Single set of scripts handles all access methods
- Shared utilities eliminate code duplication
- Consistent error handling and logging

### Access Method Abstraction
- Local: Direct file operations and local service management
- Direct SSH: plink/pscp for remote operations
- Router Tunnel: SSH tunneling for network-isolated targets

### PC/Device Mapping Integration
- Uses `ipat_watchdog.pc_device_mapping` for dependency resolution
- Automatically installs correct device plugins per PC type
- Maintains compatibility with existing build specifications

### Enhanced Error Handling
- Comprehensive validation at each step
- Detailed error messages and troubleshooting guidance
- Automatic cleanup of resources (SSH tunnels, etc.)

### Security Features
- Encrypted password storage in `.secure` folder
- SSH host key verification
- Code signing with certificate validation

## Migration from Legacy Scripts

### Quick Migration Guide

1. **Identify your current folder**: admin, router_admin, or sub_admin
2. **Map to new configuration**:
   - `admin` → `admin`
   - `router_admin` → `router_admin`
   - `sub_admin` → `sub_admin`
3. **Update your calls**:
   ```powershell
   # Old way
   cd scripts\infra\windows\app_pipelines\admin
   .\full_pipeline.ps1
   
   # New way
   cd scripts\infra\windows\consolidated_pipelines
   .\full_pipeline.ps1 -AccessConfig "admin"
   ```

### Configuration Verification

Before using the new scripts, verify your access configuration:

```powershell
# Test environment setup
.\01-test.ps1 -AccessConfig "your_config"

# Verify build process
.\02-build.ps1 -AccessConfig "your_config"
```

## Troubleshooting

### Common Issues

1. **SSH Connection Failures**
   - Verify SSH keys are in the correct location
   - Check host key fingerprints
   - Ensure PuTTY tools (plink, pscp) are in PATH

2. **Build Failures**
   - Verify PC/device mapping configuration
   - Check Python environment setup
   - Ensure all dependencies are available

3. **Deployment Issues**
   - Verify target directory permissions
   - Check Windows service/task permissions
   - Ensure firewall rules allow connections

### Debug Mode

For detailed debugging, examine the individual scripts and add verbose output:

```powershell
# Enable verbose PowerShell output
$VerbosePreference = "Continue"
.\full_pipeline.ps1 -AccessConfig "your_config" -ContinueOnError
```

## Security Considerations

### Required Files

Ensure these files exist in your `.secure` folder:
- `ipat_wd.pfx`: Code signing certificate
- `pfxpass.txt`: Certificate password (encrypted)
- `{pc_name}.txt`: Target PC passwords (encrypted)
- `misch_route.txt`: Router password (for router_admin, encrypted)

### SSH Keys

For router_admin configuration:
- Place SSH private keys in `C:\Users\{user}\.ssh\`
- Use PuTTY format (.ppk) files
- Verify host key fingerprints match your environment

## Customization

### Adding New Access Configurations

1. Edit `access-configs.ps1`
2. Add new case in `Get-AccessConfig` function
3. Define connection parameters and security settings

### Extending Pipeline Steps

1. Create new script following naming pattern
2. Add case in `full_pipeline.ps1`
3. Use existing utilities for consistency

## Performance Notes

- SSH tunnel establishment adds ~3-5 seconds to operations
- Build times depend on PC/device plugin complexity
- Health checks run comprehensive validation (may take 10-30 seconds)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify access configuration matches your environment
3. Test individual pipeline steps for isolation
4. Check Windows Event Logs for service-related issues
