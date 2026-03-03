param(
    [Parameter(Mandatory = $true)]
    [string]$Repository,

    [string]$Branch = "main",

    [string]$PayloadPath = ".github/branch-protection/main.required-checks.json",

    [string]$Token = $env:GITHUB_TOKEN
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Missing GitHub token. Set GITHUB_TOKEN or pass -Token."
}

if (-not (Test-Path -LiteralPath $PayloadPath)) {
    throw "Payload file not found: $PayloadPath"
}

$payload = Get-Content -LiteralPath $PayloadPath -Raw
$uri = "https://api.github.com/repos/$Repository/branches/$Branch/protection"
$headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

Write-Host "Applying branch protection to $Repository/$Branch using $PayloadPath"

Invoke-RestMethod `
    -Method Put `
    -Uri $uri `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $payload | Out-Null

Write-Host "Branch protection updated."
