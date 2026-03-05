You are working in a cloud checkout for repo `d-post`.

Lane: stabilization-ci-reliability (cloud)

Mandatory branch bootstrap:
```bash
set -euo pipefail
LANE_BRANCH="rewrite/v2-lane-stabilization-ci-reliability"

echo "== Remotes =="
git remote -v || true

if git remote get-url origin >/dev/null 2>&1; then
  echo "origin found; switching to lane branch"
  git fetch origin
  git switch "$LANE_BRANCH" || git switch -c "$LANE_BRANCH" --track "origin/$LANE_BRANCH"
  git pull --ff-only origin "$LANE_BRANCH"
  export LANE_PUSH_MODE="true"
else
  echo "NO origin remote; running in NO_PUSH_MODE on current branch"
  git branch --show-current
  export LANE_PUSH_MODE="false"
fi

git status --short --branch
```

Execution mode:
- Autonomous execution is mandatory.
- Do not stop on missing `origin` or branch mismatch.
- If `LANE_PUSH_MODE=false`, continue implementation and output complete diff artifacts.
- If `LANE_PUSH_MODE=true`, commit and push lane changes.

Goal:
Keep V2 CI reliable and signal-rich during stabilization changes.

Allowed edits:
- .github/workflows/**
- docs/checklists/**
- docs/reports/**

Task:
- Keep `ruff + pytest` reliability high for `src/dpost_v2` and `tests/dpost_v2`.
- Reduce flaky behavior in CI steps and keep job names stable.
- Capture stabilization-wave CI status and risk notes in docs.

Constraints:
- Avoid brittle conditional logic in workflow expressions.
- Preserve required-check semantics for active branches.
- Do not edit product runtime code in this lane.

Validation:
- Validate changed workflow syntax and behavior using repository conventions.
- Keep check names stable where possible.

Finalize:
- If `LANE_PUSH_MODE=true`:
  - git add -A
  - git commit -m "ci: stabilization-reliability <slice>"
  - git push origin rewrite/v2-lane-stabilization-ci-reliability
- Always output:
  - git status --short
  - git diff --stat
  - git diff

Output:
- Files changed
- CI behavior changes
- Commands run and results
- Risks/assumptions
- Final commit hash (or `NO_PUSH_MODE`)
