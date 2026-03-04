param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [Parameter(Mandatory = $true)]
    [string]$Lane
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lane-map.ps1"

$laneMap = Get-LaneMap
if (-not $laneMap.Contains($Lane)) {
    Write-Error "Unknown lane '$Lane'"
    exit 1
}

$worktreePath = Join-Path (Join-Path $WorkspaceRoot ".worktrees") $Lane
if (-not (Test-Path -LiteralPath $worktreePath)) {
    Write-Error "Worktree missing for $Lane. Run task `codex:lanes:setup-worktrees` first."
    exit 1
}

Set-Location -LiteralPath $worktreePath
$branch = $laneMap[$Lane].Branch

& git switch $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to switch branch '$branch' for lane '$Lane'"
    exit 1
}

& git pull --ff-only origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to fast-forward '$branch' from origin for lane '$Lane'"
    exit 1
}

Write-Host "Ready: $Lane"
