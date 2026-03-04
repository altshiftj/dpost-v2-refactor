You are working in D:\Repos\d-post.

Lane: domain-core-models
Branch: rewrite/v2-lane-domain-core-models

Goal:
Implement domain models/rules in TDD order.

Allowed edits:
- src/dpost_v2/domain/**
- tests/dpost_v2/domain/**

Canonical references:
- docs/pseudocode/domain/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Write failing deterministic domain tests.
2. Implement minimal domain logic to pass.
3. Refactor while preserving deterministic behavior.

Constraints:
- Domain layer stays pure (no I/O).
- Do not edit outside allowed scope.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
