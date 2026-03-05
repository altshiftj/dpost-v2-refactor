You are working in D:\Repos\d-post\.worktrees\stabilization-observability-quality.

Lane: stabilization-observability-quality
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

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

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
