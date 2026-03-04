You are working in D:\Repos\d-post\.worktrees\infrastructure-adapters.

Lane: infrastructure-adapters
Worktree mode (mandatory):
- Run all commands, edits, and commits from this lane worktree path only.
- Do not run lane implementation work from D:\Repos\d-post root checkout.
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Phase 2 (hardening + gap closure): harden infrastructure adapters and close remaining mapped adapter gaps in TDD order.

Allowed edits:
- src/dpost_v2/infrastructure/**
- tests/dpost_v2/infrastructure/**

Canonical references:
- docs/pseudocode/infrastructure/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

Phase focus (mandatory):
- Prioritize reliability and failure-path behavior across storage, sync, runtime UI, and observability adapters.
- Add integration-style tests for adapter interactions at contract boundaries (not just isolated happy paths).
- Treat scaffolding-only changes as out of scope unless required to close a mapped implementation gap.

TDD protocol (mandatory):
1. Write failing adapter contract/behavior tests.
2. Implement minimal adapter code.
3. Refactor while preserving contracts.

Constraints:
- Keep side effects isolated to infrastructure.
- Do not edit outside allowed scope.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions

