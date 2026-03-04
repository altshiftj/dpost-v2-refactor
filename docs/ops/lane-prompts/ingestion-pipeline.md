You are working in D:\Repos\d-post.

Lane: ingestion-pipeline
Branch: rewrite/v2-lane-ingestion-pipeline

Goal:
Implement ingestion/pipeline orchestration in TDD order.

Allowed edits:
- src/dpost_v2/application/ingestion/**
- tests/dpost_v2/application/ingestion/**

Canonical references:
- docs/pseudocode/application/ingestion/**
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md

TDD protocol (mandatory):
1. Write failing tests for stage behavior and orchestration.
2. Implement minimal pipeline logic.
3. Refactor while preserving stage contracts.

Constraints:
- Keep stage boundaries explicit.
- Do not edit outside allowed scope.

Output:
- Files changed
- Tests added/updated
- Commands run and results
- Risks/assumptions
