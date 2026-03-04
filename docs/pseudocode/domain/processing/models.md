---
id: domain/processing/models.py
origin_v1_files:
  - src/dpost/domain/processing/models.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Processing domain types and outcome models.

## Origin Gist
- Source mapping: `src/dpost/domain/processing/models.py`.
- Legacy gist: Retains processing domain model or policy models.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Processing domain types and outcome models.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Domain processing facts from stage-level computations (status flags, classification codes, reason tokens).
- Normalized severity/retryability hints from policy layer inputs.
- Candidate identity metadata required for outcome attribution.
- Optional prior outcome for transition validation.

## Outputs
- Core domain models (`ProcessingStatus`, `ProcessingOutcome`, `ProcessingReason`).
- Outcome constructors for success/reject/failure/retry domain states.
- Validation helpers enforcing legal status/reason combinations.
- Serialization-safe representations for cross-layer contracts.

## Invariants
- Every `ProcessingOutcome` has exactly one terminal status category.
- Retry outcomes include retry metadata; non-retry outcomes do not.
- Reason codes are non-empty and machine-readable.
- Example: `status=retry` with delay metadata is valid.
- Counterexample: `status=success` with failure reason code is invalid.

## Failure Modes
- Invalid status enum token raises `ProcessingStatusError`.
- Illegal status/reason combination raises `ProcessingOutcomeConsistencyError`.
- Missing required metadata for status type raises `ProcessingOutcomeMetadataError`.
- Unknown reason namespace raises `ProcessingReasonNamespaceError`.

## Pseudocode
1. Define immutable enums/models for processing statuses, reasons, and terminal categories.
2. Implement factory helpers for each terminal category enforcing required metadata.
3. Implement validator ensuring consistency between status, reason code, and retry metadata.
4. Expose conversion helper from policy classification to domain outcome model.
5. Provide serializer/deserializer helpers preserving stable wire fields.
6. Reject invalid combinations with typed domain errors.

## Tests To Implement
- unit: valid/invalid status combinations, retry metadata rules, and reason namespace validation.
- integration: ingestion policies convert failures into domain processing outcomes consumed consistently by application contracts.



