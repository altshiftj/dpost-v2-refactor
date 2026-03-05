You are working in a cloud checkout for repo `d-post`.

Lane: stabilization-observability-quality (cloud)

Mandatory branch bootstrap:
```bash
set -euo pipefail
LANE_BRANCH="rewrite/v2-lane-stabilization-observability-quality"

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
Improve observability quality for V2 startup/runtime so diagnostics are explicit, stable, and testable.

Allowed edits:
- src/dpost_v2/infrastructure/observability/**
- src/dpost_v2/application/startup/**
- src/dpost_v2/runtime/**
- tests/dpost_v2/infrastructure/observability/**
- tests/dpost_v2/application/startup/**
- tests/dpost_v2/runtime/**

Task:
- Audit startup event payload consistency for mode/profile/provenance/plugin visibility.
- Standardize log/event fields needed for manual diagnostics and CI assertions.
- Add regression tests for event/log contract stability.

Constraints:
- Do not edit outside allowed scope.
- Keep event names and payload keys stable once hardened.
- Avoid introducing noisy logs that reduce signal quality.

Validation:
- python -m ruff check src/dpost_v2 tests/dpost_v2
- python -m pytest -q tests/dpost_v2/infrastructure/observability tests/dpost_v2/runtime tests/dpost_v2/application/startup

Finalize:
- If `LANE_PUSH_MODE=true`:
  - git add -A
  - git commit -m "v2: stabilization-observability-quality <slice>"
  - git push origin rewrite/v2-lane-stabilization-observability-quality
- Always output:
  - git status --short
  - git diff --stat
  - git diff

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
- Final commit hash (or `NO_PUSH_MODE`)
