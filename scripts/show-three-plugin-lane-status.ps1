$repoRoot = Split-Path -Parent $PSScriptRoot
$laneNames = @(
    "laneA-sem-phenomxl2",
    "laneB-utm-zwick",
    "laneC-psa-horiba"
)

foreach ($laneName in $laneNames) {
    $worktree = Join-Path $repoRoot ".worktrees\\$laneName"
    $head = git -C $worktree rev-parse --short HEAD
    $status = git -C $worktree status --short --branch
    $lastPath = Join-Path $worktree "codex-last-message.txt"

    Write-Host ""
    Write-Host "[$laneName]"
    Write-Host "HEAD: $head"
    Write-Host $status
    if (Test-Path $lastPath) {
        Write-Host "--- last message ---"
        Get-Content $lastPath
    } else {
        Write-Host "--- last message ---"
        Write-Host "<missing>"
    }
}
