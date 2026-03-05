You are working in a cloud checkout for repo `d-post`.

Lane: stabilization-ingestion-robustness (cloud)

Mandatory branch bootstrap:
```bash
set -euo pipefail
LANE_BRANCH="rewrite/v2-lane-stabilization-ingestion-robustness"

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
Harden V2 ingestion behavior for malformed inputs and failure transitions while preserving deterministic outcomes.

Allowed edits:
- src/dpost_v2/application/ingestion/**
- tests/dpost_v2/application/ingestion/**

Task:
- Strengthen retry/failure transition coverage and deterministic failure outcomes.
- Validate malformed, empty, and partial input behavior.
- Preserve stage boundaries and contract semantics.

TDD protocol (mandatory):
1. Write failing tests for robustness/failure-path behavior.
2. Implement minimal ingestion changes.
3. Refactor while keeping stage contracts stable.

Constraints:
- Do not edit outside allowed scope.
- Do not weaken existing stage contract tests to make failures disappear.

Validation:
- python -m ruff check src/dpost_v2 tests/dpost_v2
- python -m pytest -q tests/dpost_v2/application/ingestion

Finalize:
- If `LANE_PUSH_MODE=true`:
  - git add -A
  - git commit -m "v2: stabilization-ingestion-robustness <slice>"
  - git push origin rewrite/v2-lane-stabilization-ingestion-robustness
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
