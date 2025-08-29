# Windows Infrastructure Scripts

This directory contains PowerShell-based deployment and management scripts for the IPAT Data Watchdog application on Windows environments. The scripts are organized into different pipeline configurations to support various deployment scenarios and administrative access levels.

## Directory Structure

```
scripts/infra/windows/
├── app_pipelines/          # Application deployment pipelines
│   ├── admin/             # Direct admin access deployment
│   ├── router_admin/      # Router-based deployment (via Linux jump host)
│   └── sub_admin/         # Subprocess-based deployment
└── utils/                 # Shared utilities and helper scripts
```

## Pipeline Overview

Each pipeline follows a standardized structure with numbered scripts that execute in sequence:

1. **00-env.ps1** - Environment configuration and variable setup
2. **01-test.ps1** - Pre-deployment testing and validation
3. **02-build.ps1** - Application building and packaging
4. **03-sign.ps1** - Code signing for security compliance
5. **04-deploy.ps1** - Deployment to target systems
6. **05-run.ps1** - Application startup and initialization
7. **06-health_check.ps1** - Post-deployment health verification
8. **07-rollback.ps1** - Rollback procedures (where applicable)
9. **full_pipeline.ps1** - Orchestrates complete deployment workflow

## Pipeline Types

### Admin Pipeline (`app_pipelines/admin/`)

**Purpose**: Direct deployment with full administrative privileges on the target system.

**Use Cases**:
- Development and testing environments
- Systems with direct administrative access
- Local deployments and debugging scenarios

**Characteristics**:
- Direct file system access
- Native PowerShell remoting
- Full administrative privileges required
- Simplest configuration and fastest execution

**Best For**: 
- Development teams with direct access to target systems
- Testing environments where security restrictions are minimal
- Quick iteration and debugging cycles

### Router Admin Pipeline (`app_pipelines/router_admin/`)

**Purpose**: Deployment through a Linux router/jump host to reach target Windows systems.

**Use Cases**:
- Production environments with network segmentation
- Systems behind firewalls or in DMZs
- Cross-platform deployment scenarios

**Characteristics**:
- Uses SSH tunneling through Linux router
- PuTTY tools (plink, pscp) for Windows-to-Linux communication
- SSH key-based authentication
- More complex networking setup required

**Best For**:
- Production deployments with security requirements
- Network-isolated target systems
- Environments requiring audit trails through jump hosts

**Technical Details**:
- Establishes SSH tunnel: Windows → Linux Router → Target Windows PC
- Supports both password and SSH key authentication
- Includes comprehensive connectivity testing
- Handles host key verification and secure credential management
- Uses PowerShell 5 and PuTTY tools for backwards compatibility with older Windows systems

### Sub Admin Pipeline (`app_pipelines/sub_admin/`)

**Purpose**: Deployment using subprocess execution for environments with restricted direct access.

**Use Cases**:
- Environments with process isolation requirements
- Systems with limited PowerShell remoting capabilities
- Containerized or sandboxed deployment scenarios

**Characteristics**:
- Uses subprocess execution for isolation
- Reduced dependency on PowerShell remoting
- Can work with limited privileges in some scenarios
- More robust error handling for process management

**Best For**:
- Environments with strict process isolation policies
- Systems where PowerShell remoting is restricted
- Deployment scenarios requiring process-level security boundaries

**Note**: This pipeline does not include a rollback script (07-rollback.ps1) as subprocess-based deployments typically use different rollback strategies.

## Utilities (`utils/`)

### ci_context.ps1
Provides CI/CD context detection and environment variable management for automated builds.

### create_secure_pw.ps1
Utility for creating and managing secure password storage for deployment authentication.

### register_task.ps1
Helper script for registering Windows scheduled tasks for the IPAT Data Watchdog service.

## Script Descriptions

### 00-env.ps1 (Environment Configuration)
- Sets up deployment variables and paths
- Configures authentication credentials
- Establishes network and system parameters
- Loads environment-specific settings

### 01-test.ps1 (Pre-deployment Testing)
- Builds the IPAT Data Watchdog application
- Runs pytest test suite to validate functionality
- Ensures code quality before deployment
- Validates that all tests pass before proceeding with deployment

### 02-build.ps1 (Build and Package)
- Compiles the IPAT Data Watchdog application
- Creates deployment packages
- Handles dependency management
- Prepares artifacts for deployment

### 03-sign.ps1 (Code Signing)
- Digitally signs executables for security
- Validates signing certificates
- Prepares signed artifacts for deployment

### 04-deploy.ps1 (Deployment)
- Transfers application files to target systems
- Configures system settings and services
- Handles deployment verification

### 05-run.ps1 (Application Startup)
- Starts the IPAT Data Watchdog service
- Configures runtime parameters
- Initializes application components
- Verifies successful startup

### 06-health_check.ps1 (Health Verification)
- Performs post-deployment health checks
- Validates service functionality
- Tests application endpoints

### 07-rollback.ps1 (Rollback Procedures)
- Provides rollback capabilities for failed deployments
- Restores previous application versions
- Handles cleanup of failed deployment artifacts
- Returns system to known good state

### full_pipeline.ps1 (Complete Workflow)
- Orchestrates the entire deployment process
- Handles error conditions and retries
- Provides comprehensive logging
- Manages pipeline execution flow

## Usage Guidelines

### Choosing the Right Pipeline

1. **Use Admin Pipeline When**:
   - You have direct administrative access to target systems
   - Working in development or testing environments
   - Network security restrictions are minimal
   - Speed and simplicity are priorities

2. **Use Router Admin Pipeline When**:
   - Target systems are network-isolated or behind firewalls
   - Production security requirements mandate jump host usage
   - Cross-platform deployment (Windows → Linux → Windows) is needed
   - Audit trails through jump hosts are required

3. **Use Sub Admin Pipeline When**:
   - Process isolation is required for security
   - PowerShell remoting is restricted or unavailable

### Execution Order

Execute scripts in numerical order:
```powershell
# Example: Router Admin Pipeline
.\00-env.ps1
.\01-test.ps1
.\02-build.ps1
.\03-sign.ps1
.\04-deploy.ps1
.\05-run.ps1
.\06-health_check.ps1

# Or use the complete pipeline:
.\full_pipeline.ps1
```

### Error Handling

Each script includes error handling and logging. If any step fails:
1. Check the error logs for specific failure details
2. Verify prerequisites and configurations
3. Use rollback scripts if available to return to previous state
4. Consult pipeline-specific documentation for troubleshooting

### Security Considerations

- **Credentials**: Use secure credential storage mechanisms
- **SSH Keys**: Use SSH key authentication
- **Code Signing**: Ensure valid certificates for production deployments
- **Network**: Verify firewall rules and network connectivity
- **Permissions**: Validate that deployment accounts have necessary privileges

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Verify credentials in 00-env.ps1
   - Check SSH key configuration for pipeline
   - Validate certificate store access for signing

2. **Network Connectivity**:
   - Test connectivity with 01-test.ps1
   - Verify firewall rules and port access
   - Check SSH tunnel establishment for router pipeline

3. **Permission Errors**:
   - Ensure deployment account has necessary privileges
   - Verify service account permissions
   - Check file system access rights

4. **Build Failures**:
   - Validate development environment setup
   - Check dependency availability
   - Verify build tool versions and paths

### Getting Help

For deployment issues:
1. Review the specific pipeline's script comments
2. Check the deployment logs generated by each script
3. Consult the main project documentation
4. Verify system prerequisites and configurations

## Development Notes

When modifying these scripts:
- Maintain the numbered script sequence
- Preserve error handling patterns
- Update corresponding documentation
- Test changes across all pipeline types
- Follow PowerShell best practices for cross-version compatibility

### Compatibility Requirements

The pipeline scripts are designed with backwards compatibility in mind:
- **PowerShell 5**: Scripts target PowerShell 5.1 to support older Windows systems that may not have PowerShell 7+ installed
- **PuTTY Tools**: Router admin pipeline uses PuTTY (plink, pscp) instead of native SSH to ensure compatibility with legacy Windows versions

The pipeline scripts are designed to be modular and reusable across different deployment scenarios while maintaining consistency in structure and behavior.
