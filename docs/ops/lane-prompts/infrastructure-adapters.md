You are working in D:\Repos\d-post.

Lane: infrastructure-adapters
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Implement infrastructure adapters in TDD order.

Allowed edits:
- src/dpost_v2/infrastructure/**
- tests/dpost_v2/infrastructure/**

Canonical references:
- docs/pseudocode/infrastructure/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

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

