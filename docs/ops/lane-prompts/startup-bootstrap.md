You are working in D:\Repos\d-post.

Lane: startup-bootstrap
Branch: rewrite/v2-lane-startup-bootstrap

Goal:
Implement startup/bootstrap orchestration in TDD order.

Allowed edits:
- src/dpost_v2/application/startup/**
- src/dpost_v2/runtime/**
- tests/dpost_v2/application/startup/**
- tests/dpost_v2/runtime/**

Canonical references:
- docs/pseudocode/** (startup/runtime related)
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Write failing startup/bootstrap tests first.
2. Implement minimal composition/bootstrap code.
3. Refactor with tests green.

Constraints:
- Do not edit outside allowed scope.
- Keep startup deterministic and explicit.
- No hidden global wiring.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
