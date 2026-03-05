You are working in D:\Repos\d-post\.worktrees\records-core.

Lane: records-core
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Implement V2 application records service in TDD order.

Allowed edits:
- src/dpost_v2/application/records/**
- tests/dpost_v2/application/records/**

Canonical references:
- docs/pseudocode/application/records/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Write failing tests for create/update/mark_unsynced/save behavior.
2. Implement minimal records service code.
3. Refactor while preserving deterministic behavior and typed error mapping.

Constraints:
- Keep application layer boundaries explicit.
- Do not edit outside allowed scope.
- Keep storage adapter specifics behind record store port semantics.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
