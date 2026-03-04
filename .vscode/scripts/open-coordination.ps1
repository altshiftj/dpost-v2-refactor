param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    Write-Error "Workspace root not found: $WorkspaceRoot"
    exit 1
}

Set-Location -LiteralPath $WorkspaceRoot
& git switch rewrite/v2
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to switch to rewrite/v2 in $WorkspaceRoot"
    exit 1
}

& git pull --ff-only origin rewrite/v2
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to fast-forward 'rewrite/v2' from origin in $WorkspaceRoot"
    exit 1
}

Write-Host "Ready: coordination terminal on rewrite/v2"
