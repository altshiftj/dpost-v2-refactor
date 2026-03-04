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

. "$PSScriptRoot/lane-map.ps1"

$laneMap = Get-LaneMap
$base = Join-Path $WorkspaceRoot ".worktrees"
New-Item -ItemType Directory -Force -Path $base | Out-Null

foreach ($lane in $laneMap.Keys) {
    $worktreePath = Join-Path $base $lane
    if (Test-Path -LiteralPath $worktreePath) {
        Write-Host "exists: $worktreePath"
        continue
    }

    $branch = $laneMap[$lane].Branch
    & git -C $WorkspaceRoot worktree add $worktreePath $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create worktree for lane '$lane' on branch '$branch'"
        exit 1
    }
}

Write-Host "worktree setup done"

