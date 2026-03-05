You are working in D:\Repos\d-post\.worktrees\contracts-interfaces.

Lane: contracts-interfaces
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Implement V2 contracts/interfaces in TDD order (tests first, then code).

Allowed edits:
- src/dpost_v2/application/contracts/**
- tests/dpost_v2/application/contracts/**
- tests/dpost_v2/contracts/**

Canonical references:
- docs/pseudocode/** (contract-related)
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Add or update failing tests for one contract slice.
2. Implement minimal code to pass.
3. Refactor while tests stay green.
4. Repeat in small slices.

Constraints:
- Do not edit outside allowed scope.
- Keep interfaces stable and explicit.
- Preserve V2 layer boundaries.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions

