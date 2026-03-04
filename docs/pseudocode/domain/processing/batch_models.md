---
id: domain/processing/batch_models.py
origin_v1_files:
  - src/dpost/domain/processing/batch_models.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Batch outcome/data models for grouped processing operations.

## Origin Gist
- Source mapping: `src/dpost/domain/processing/batch_models.py`.
- Legacy gist: Retains processing domain model or policy batch_models.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Batch outcome/data models for grouped processing operations.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Collection of individual `ProcessingOutcome` entries.
- Batch identity metadata (batch id, started_at, completed_at).
- Grouping keys (profile, device family, route bucket).
- Optional expected-item-count constraints.

## Outputs
- `BatchOutcome` model with aggregate counts and per-group summaries.
- Batch-level status classification (`completed`, `partial_failure`, `failed`).
- Aggregation helper functions for totals and grouped summaries.
- Validation errors for inconsistent batch payloads.

## Invariants
- Aggregate counts equal the number of unique member outcomes.
- Member identity keys are unique within a batch.
- Batch terminal status is derived solely from member outcome categories.
- Example: 10 members with 8 success + 2 retry -> aggregate count is 10.
- Counterexample: declared total 10 with 9 unique members is invalid.

## Failure Modes
- Duplicate member identity key raises `BatchMemberDuplicateError`.
- Count mismatch raises `BatchCountConsistencyError`.
- Invalid batch status derivation input raises `BatchStatusDerivationError`.
- Missing required batch identity metadata raises `BatchMetadataError`.

## Pseudocode
1. Validate batch metadata and uniqueness of member outcome identities.
2. Aggregate member outcomes into status/category counts.
3. Compute grouped summaries by configured grouping keys.
4. Derive batch terminal status from aggregate member categories.
5. Validate declared totals and optional expected count constraints.
6. Return immutable `BatchOutcome` with summary and diagnostics.

## Tests To Implement
- unit: uniqueness enforcement, count aggregation correctness, batch status derivation, and mismatch rejection.
- integration: application reporting paths consume batch models built from multiple ingestion outcomes and preserve aggregate consistency.



