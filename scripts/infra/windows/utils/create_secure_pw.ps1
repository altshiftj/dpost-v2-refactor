# create-secure-password.ps1
# Prompts for a password, encrypts it, and saves it to a specified file
param (
    [string]$OutputPath = "$env:USERPROFILE\.secure\hioki_blb.txt"
)

# Ensure the folder exists
$folder = Split-Path $OutputPath
if (-not (Test-Path $folder)) {
    New-Item -Path $folder -ItemType Directory -Force | Out-Null
}

# Prompt user for password as SecureString
$securePassword = Read-Host "Enter the password to encrypt and store" -AsSecureString

# Convert to encrypted string
$encrypted = $securePassword | ConvertFrom-SecureString

# Save to file
Set-Content -Path $OutputPath -Value $encrypted

Write-Host "Encrypted password saved to: $OutputPath"
