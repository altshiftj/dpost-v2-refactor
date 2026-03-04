You are working in D:\Repos\d-post.

Lane: runtime-composition
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Implement runtime composition/wiring in TDD order.

Allowed edits:
- src/dpost_v2/runtime/**
- src/dpost_v2/application/startup/**
- tests/dpost_v2/runtime/**
- tests/dpost_v2/application/startup/**

Canonical references:
- docs/pseudocode/runtime/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Write failing composition/bootstrap tests first.
2. Implement minimal wiring.
3. Refactor while preserving deterministic boot behavior.

Constraints:
- Do not edit outside allowed scope.
- Keep composition explicit and testable.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions

