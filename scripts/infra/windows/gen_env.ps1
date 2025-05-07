param (
  [string]$DeviceSlug = $env:DEVICE_SLUG
)

$DeviceFile = "devices/$DeviceSlug.yml"
if (-not (Test-Path $DeviceFile)) {
  Write-Error "Device file not found: $DeviceFile"
  exit 1
}

try {
  $yaml = Get-Content $DeviceFile -Raw | ConvertFrom-Yaml
} catch {
  Write-Error "Failed to parse YAML: $DeviceFile"
  exit 1
}

# Required fields
$requiredKeys = @('device_name', 'target_ip', 'target_port', 'target_user', 'target_pass')
foreach ($key in $requiredKeys) {
  if (-not $yaml.ContainsKey($key)) {
    Write-Error "Missing key '$key' in $DeviceFile"
    exit 1
  }
  if ($yaml[$key] -match '^\$\{.+\}$') {
    Write-Error "Unresolved secret variable in '$key': $($yaml[$key])"
    exit 1
  }
}

# Output .env
$envText = @"
TARGET_IP=$($yaml.target_ip)
TARGET_PORT=$($yaml.target_port)
TARGET_USER=$($yaml.target_user)
TARGET_PASS=$($yaml.target_pass)
DEVICE_NAME=$($yaml.device_name)
PLUGINS=$plugins
"@

Set-Content -Path "device.env" -Value $envText -Encoding UTF8
Write-Host "Generated device.env for [$DeviceSlug]"
