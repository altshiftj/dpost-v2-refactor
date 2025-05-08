# Parse the parameter or fallback to environment variable if not passed explicitly
param (
  [string]$DeviceSlug = $env:DEVICE_SLUG
)

# Define the path to the device YAML configuration file
$DeviceFile = "devices/$DeviceSlug.yml"

# Check if the YAML file for the given device exists
if (-not (Test-Path $DeviceFile)) {
  Write-Error "Device file not found: $DeviceFile"
  exit 1
}

# Attempt to read and parse the YAML file content into a PowerShell object
try {
  $yaml = Get-Content $DeviceFile -Raw | ConvertFrom-Yaml
} catch {
  Write-Error "Failed to parse YAML: $DeviceFile"
  exit 1
}

# Define the list of required configuration keys
$requiredKeys = @('device_name', 'target_ip', 'target_port', 'target_user', 'target_pass')

# Validate that all required keys exist and are not unresolved secret placeholders
foreach ($key in $requiredKeys) {
  if (-not $yaml.ContainsKey($key)) {
    Write-Error "Missing key '$key' in $DeviceFile"
    exit 1
  }
  # Detect unresolved environment-style secrets like ${SOME_SECRET}
  if ($yaml[$key] -match '^\$\{.+\}$') {
    Write-Error "Unresolved secret variable in '$key': $($yaml[$key])"
    exit 1
  }
}

# Build a .env-style text block for use in CI/CD or runtime environments
$envText = @"
TARGET_IP=$($yaml.target_ip)
TARGET_PORT=$($yaml.target_port)
TARGET_USER=$($yaml.target_user)
TARGET_PASS=$($yaml.target_pass)
DEVICE_NAME=$($yaml.device_name)
PLUGINS=$plugins
"@

# Write the generated environment variables to a file
Set-Content -Path "device.env" -Value $envText -Encoding UTF8

# Notify the user that the operation was successful
Write-Host "Generated device.env for [$DeviceSlug]"
