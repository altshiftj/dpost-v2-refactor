You are working in D:\Repos\d-post.

Lane: contracts-interfaces
Branch: rewrite/v2-lane-contracts-interfaces

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
