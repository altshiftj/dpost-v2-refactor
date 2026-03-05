You are working in a cloud checkout for repo `d-post`.

Lane: stabilization-runtime-resilience (cloud)

Mandatory branch bootstrap:
```bash
set -euo pipefail
LANE_BRANCH="rewrite/v2-lane-stabilization-runtime-resilience"

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
Harden V2 startup/runtime resilience so repeated launches and failure paths stay deterministic.

Allowed edits:
- src/dpost_v2/__main__.py
- src/dpost_v2/runtime/**
- src/dpost_v2/application/startup/**
- tests/dpost_v2/test___main__.py
- tests/dpost_v2/runtime/**
- tests/dpost_v2/application/startup/**

Task:
- Validate and harden idempotent startup/shutdown behavior.
- Ensure failure paths preserve stable exit-code behavior and structured startup events.
- Keep dry-run and non-dry-run cleanup behavior consistent where applicable.

Constraints:
- Do not edit outside allowed scope.
- Do not reintroduce retired runtime modes (`v1`, `shadow`).
- Preserve `dpost` as the canonical command surface.

Validation:
- python -m ruff check src/dpost_v2 tests/dpost_v2
- python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/runtime tests/dpost_v2/application/startup

Finalize:
- If `LANE_PUSH_MODE=true`:
  - git add -A
  - git commit -m "v2: stabilization-runtime-resilience <slice>"
  - git push origin rewrite/v2-lane-stabilization-runtime-resilience
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
