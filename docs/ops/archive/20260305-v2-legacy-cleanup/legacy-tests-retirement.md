ARCHIVE STATUS:
- Historical lane prompt from V2 cutover.
- Retained for audit traceability; not an active runtime/runbook target.

You are working in D:\Repos\d-post\.worktrees\legacy-tests-retirement.

Lane: legacy-tests-retirement
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

Goal:
Retire legacy test suites that validate the removed legacy runtime surface.

Context decisions (locked):
- Command name remains `dpost`.
- Legacy runtime modes `v1` and `shadow` are retired.

Allowed edits:
- tests/unit/**
- tests/integration/**
- tests/manual/**
- tests/helpers/**
- tests/conftest.py

Task:
- Remove legacy test directories that target `src/dpost`.
- Keep V2 test harness (`tests/dpost_v2`) untouched.
- Ensure no stale references remain in retained test files under allowed scope.

TDD protocol (mandatory):
1. Add/update tests only if required to protect retained V2 test behavior.
2. Implement minimal removal/refactor changes.
3. Refactor for clear ownership of active test surfaces.

Constraints:
- Do not edit outside allowed scope.
- Do not modify `tests/dpost_v2/**`.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
