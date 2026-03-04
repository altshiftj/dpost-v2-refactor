---
id: domain/records/local_record.py
origin_v1_files:
  - src/dpost/domain/records/local_record.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Local record entity contract and invariants.

## Origin Gist
- Source mapping: `src/dpost/domain/records/local_record.py`.
- Legacy gist: Retains record entity contract local_record.py in domain layer.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Local record entity contract and invariants.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Record identity attributes (record id, source identity, canonical name key).
- Record state fields (sync status, processing status, timestamps, revision).
- Domain mutation intents (`create`, `apply_processing_result`, `mark_unsynced`, `mark_synced`).
- Validation constraints (required fields, legal state transitions).

## Outputs
- Immutable `LocalRecord` entity model.
- Domain mutation methods returning new record instances.
- Validation result for record integrity and transition legality.
- Domain comparison helpers (identity equality vs revision differences).

## Invariants
- `record_id` and identity fields are immutable once created.
- Revision value is monotonic for accepted mutations.
- Sync status transitions follow explicit state graph.
- Example: `synced -> unsynced` via `mark_unsynced` is valid and increments revision.
- Counterexample: mutation lowering revision or changing `record_id` is invalid.

## Failure Modes
- Missing required identity fields raises `LocalRecordIdentityError`.
- Illegal state transition raises `LocalRecordTransitionError`.
- Revision regression raises `LocalRecordRevisionError`.
- Invalid timestamp ordering raises `LocalRecordTimestampError`.

## Pseudocode
1. Define immutable `LocalRecord` with identity, status, revision, and timestamp fields.
2. Implement `create_record` constructor enforcing mandatory identity constraints.
3. Implement mutation helpers that return new instances and increment revision deterministically.
4. Validate sync/processing status transition legality for each mutation helper.
5. Enforce timestamp ordering rules when applying mutations.
6. Return typed domain errors on integrity or transition violations.

## Tests To Implement
- unit: identity immutability, revision monotonicity, legal/illegal sync transitions, and timestamp validation.
- integration: application records service operations preserve local record domain invariants across persist/post-persist update flows.



