param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [Parameter(Mandatory = $true)]
    [string]$PromptRelativePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$promptPath = Join-Path $WorkspaceRoot $PromptRelativePath
if (-not (Test-Path -LiteralPath $promptPath)) {
    Write-Error "Prompt file not found: $promptPath"
    exit 1
}

Get-Content -LiteralPath $promptPath -Raw | Set-Clipboard
Write-Host "Copied: $PromptRelativePath"
