param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [Parameter(Mandatory = $true)]
    [string]$PromptRelativePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    Write-Error "Workspace root not found: $WorkspaceRoot"
    exit 1
}

$promptPath = Join-Path $WorkspaceRoot $PromptRelativePath
if (-not (Test-Path -LiteralPath $promptPath)) {
    Write-Error "Prompt file not found: $promptPath"
    exit 1
}

$promptContent = Get-Content -LiteralPath $promptPath -Raw
Set-Clipboard -Value $promptContent
Write-Host "Copied: $PromptRelativePath"

