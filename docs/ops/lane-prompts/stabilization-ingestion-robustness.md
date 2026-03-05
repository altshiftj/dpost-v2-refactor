You are working in D:\Repos\d-post\.worktrees\stabilization-ingestion-robustness.

Lane: stabilization-ingestion-robustness
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.

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

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
