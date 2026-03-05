You are working in D:\Repos\d-post\.worktrees\stabilization-ci-reliability.

Lane: stabilization-ci-reliability
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

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

Output:
- Files changed
- CI behavior changes
- Commands run and results
- Risks/assumptions
