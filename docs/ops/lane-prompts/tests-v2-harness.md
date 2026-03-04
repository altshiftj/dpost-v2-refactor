You are working in D:\Repos\d-post.

Lane: tests-v2-harness
Autonomy mode (mandatory):
- Execute fully autonomously until the lane task is complete.
- Do not ask for human input during normal implementation flow.
- Only stop/ask if hard-blocked by missing credentials, unavailable required external systems, or contradictory instructions.
Goal:
Build V2 test harness/fixtures/utilities in TDD-friendly form.

Allowed edits:
- tests/dpost_v2/**
- src/dpost_v2/** (only shared test-support code when unavoidable)

Canonical references:
- docs/pseudocode/** (testing-related)
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md

TDD protocol (mandatory):
1. Add failing tests for harness behavior itself.
2. Implement minimal harness utilities/fixtures.
3. Refactor while keeping test ergonomics and determinism.

Constraints:
- Prefer test-side utilities under `tests/dpost_v2`.
- Keep fixtures deterministic.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions

