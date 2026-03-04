---
id: application/records/service.py
origin_v1_files:
  - src/dpost/application/records/record_manager.py
lane: Records-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Record lifecycle API (`create`, `update`, `mark_unsynced`, `save`) via record port.

## Origin Gist
- Source mapping: `src/dpost/application/records/record_manager.py`.
- Legacy gist: Defines records service over explicit store contract.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Record lifecycle API (`create`, `update`, `mark_unsynced`, `save`) via record port.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Record mutation intents from ingestion stages (`create`, `update`, `mark_unsynced`, `save`).
- Domain record models from `domain.records.local_record`.
- Persistence port calls via `RecordStorePort`.
- Correlation context for audit and event emission metadata.

## Outputs
- Persisted `LocalRecord` snapshots with version metadata.
- Mutation result model including created/updated/no-op classification.
- Unsynced markers consumed by sync infrastructure.
- Typed persistence errors mapped for ingestion failure policies.

## Invariants
- Record key identity is stable and unique.
- Version/revision fields are monotonic for successful writes.
- `mark_unsynced(record_id)` is idempotent when record is already unsynced.
- Service enforces domain validation before calling persistence adapters.

## Failure Modes
- Missing record on update/mark call yields `RecordNotFoundError`.
- Domain validation failure yields `RecordValidationError`.
- Store conflict (optimistic concurrency/version mismatch) yields `RecordConflictError`.
- Store unavailability or timeout yields `RecordStoreError`.

## Pseudocode
1. Define application-level `RecordsService` API wrapping `RecordStorePort` operations with domain validation.
2. Implement `create_record(input)` that builds domain model, validates invariants, and persists with initial revision.
3. Implement `update_record(record_id, mutation)` that loads current record, applies mutation, validates, and saves with conflict guard.
4. Implement `mark_unsynced(record_id)` as idempotent flag update with no-op outcome when already unsynced.
5. Implement `save_record(record)` as explicit persistence boundary returning typed success/error outcomes.
6. Emit optional record lifecycle events using event port without leaking adapter-specific exceptions.

## Tests To Implement
- unit: create/update validation, idempotent `mark_unsynced`, and conflict mapping from store errors.
- integration: ingestion persist/post-persist stages call records service and observe deterministic mutation outcomes across create/update/retry flows.



