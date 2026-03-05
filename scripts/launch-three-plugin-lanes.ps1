param(
    [string]$Profile = "auto_xhi",
    [switch]$Yolo
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$specLockCommit = "b33d33e"
$laneDefs = @(
    @{
        Name = "laneA-sem-phenomxl2"
        Worktree = Join-Path $repoRoot ".worktrees\\laneA-sem-phenomxl2"
        Prompt = Join-Path $repoRoot "docs\\ops\\lane-prompts\\three-plugin-laneA-sem-phenomxl2.md"
    },
    @{
        Name = "laneB-utm-zwick"
        Worktree = Join-Path $repoRoot ".worktrees\\laneB-utm-zwick"
        Prompt = Join-Path $repoRoot "docs\\ops\\lane-prompts\\three-plugin-laneB-utm-zwick.md"
    },
    @{
        Name = "laneC-psa-horiba"
        Worktree = Join-Path $repoRoot ".worktrees\\laneC-psa-horiba"
        Prompt = Join-Path $repoRoot "docs\\ops\\lane-prompts\\three-plugin-laneC-psa-horiba.md"
    }
)

function Assert-LaneHead {
    param(
        [string]$Worktree,
        [string]$ExpectedCommit
    )

    $head = git -C $Worktree rev-parse --short HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read git HEAD for $Worktree"
    }
    if ($head.Trim() -ne $ExpectedCommit) {
        throw "Worktree $Worktree is at $head, expected $ExpectedCommit"
    }
}

$started = @()
foreach ($lane in $laneDefs) {
    Assert-LaneHead -Worktree $lane.Worktree -ExpectedCommit $specLockCommit

    $logPath = Join-Path $lane.Worktree "codex-exec.log"
    $lastPath = Join-Path $lane.Worktree "codex-last-message.txt"
    foreach ($path in @($logPath, $lastPath)) {
        if (Test-Path $path) {
            Remove-Item $path -Force
        }
    }

    $yoloFlag = if ($Yolo.IsPresent) {
        "--dangerously-bypass-approvals-and-sandbox"
    } else {
        ""
    }

    $command = @"
Get-Content '$($lane.Prompt)' -Raw |
codex exec -p $Profile $yoloFlag -C '$($lane.Worktree)' --json -o '$lastPath' - *> '$logPath'
"@

    $proc = Start-Process `
        -FilePath pwsh `
        -WorkingDirectory $repoRoot `
        -ArgumentList @("-NoProfile", "-Command", $command) `
        -PassThru

    $started += [PSCustomObject]@{
        lane = $lane.Name
        pid = $proc.Id
        worktree = $lane.Worktree
        log = $logPath
        last = $lastPath
    }
}

$started | Format-Table -AutoSize
