You are working in D:\Repos\d-post\.worktrees\stabilization-runtime-resilience.

Lane: stabilization-runtime-resilience
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

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

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
