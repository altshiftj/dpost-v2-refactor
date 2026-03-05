# Checklist: V2 Records-Core Lane Completion

## Objective
- Verify that V2 application records service behavior (`create`, `update`, `mark_unsynced`, `save`) was implemented in TDD order with deterministic outcomes and typed error mapping.

## Reference Set
- `docs/pseudocode/application/records/README.md`
- `docs/pseudocode/application/records/service.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: TDD Red-Green Sequence
- Why this matters: lane quality depends on proving behavior through failing tests first, then minimal implementation.

### Checklist
- [x] Added failing tests for service-level validation and normalization behavior in `tests/dpost_v2/application/records/test_service.py`.
- [x] Confirmed red state before implementation (`5 failed, 6 passed`).
- [x] Implemented minimal service changes in `src/dpost_v2/application/records/service.py`.
- [x] Confirmed green state after implementation (`11 passed`).

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/records/test_service.py`

### Completion Notes
- How it was done: tests were added first for pre-store validation and `record_id` normalization, then service logic was updated to satisfy only the new required assertions while preserving existing behavior.

---

## Section: Create/Save Validation Boundaries
- Why this matters: the application layer must validate domain invariants before crossing the record-store port.

### Checklist
- [x] Enforced strict `LocalRecord` validation in `_to_store_payload` (identity fields, enum membership, non-negative revision, timestamp ordering, metadata token shape).
- [x] Ensured invalid `create` inputs fail with `RecordValidationError` before any store call.
- [x] Ensured invalid `save` inputs fail with `RecordValidationError` before any store call.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/records/test_service.py -k "create_validates_record_before_store_call or save_validates_record_before_store_call"`

### Completion Notes
- How it was done: validation logic was centralized in payload normalization so both `create` and `save` share one deterministic contract gate.

---

## Section: Update Mutation Contract
- Why this matters: update semantics must remain port-agnostic and reject malformed mutation requests at the application boundary.

### Checklist
- [x] Added mutation normalization requiring `mutation.expected_revision`.
- [x] Added mutation normalization requiring `mutation.payload` to be a mapping.
- [x] Ensured malformed mutation requests fail as `RecordValidationError` before store update calls.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/records/test_service.py -k "update_requires_expected_revision_before_store_call or update_requires_payload_mapping_before_store_call"`

### Completion Notes
- How it was done: introduced `_normalize_mutation(...)` to validate and normalize update input before delegating to `RecordStorePort.update(...)`.

---

## Section: Mark Unsynced Determinism
- Why this matters: `mark_unsynced` must be idempotent and deterministic across input variations.

### Checklist
- [x] Preserved idempotent `mark_unsynced` behavior when record is already unsynced.
- [x] Added `record_id` normalization so whitespace-wrapped ids resolve to canonical ids.
- [x] Reused normalized `record_id` across read/mark/read flow.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/records/test_service.py -k "mark_unsynced"`

### Completion Notes
- How it was done: introduced `_normalize_record_id(...)` and applied it consistently in `update`, `mark_unsynced`, and snapshot retrieval.

---

## Section: Typed Error Mapping Preservation
- Why this matters: ingestion and retry policies rely on stable typed failure categories.

### Checklist
- [x] Preserved store-exception mapping to `RecordNotFoundError`, `RecordConflictError`, `RecordValidationError`, and `RecordStoreError`.
- [x] Kept not-found/conflict mapping behavior compatible with existing tests.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/application/records/test_service.py -k "maps_missing_record_to_not_found_error or maps_conflict_to_record_conflict_error"`

### Completion Notes
- How it was done: refactor was constrained to input normalization and payload validation; exception mapping logic remained unchanged.

---

## Section: Lane Validation Gate
- Why this matters: lane handoff requires reproducible green checks beyond the local test file.

### Checklist
- [x] Ran lane lint checks.
- [x] Ran full V2 test suite to confirm no regressions.
- [x] Recorded lane checkpoint commit.

### Manual Check
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `git show --stat --oneline -1`

### Completion Notes
- How it was done: full validation passed (`346 passed`), and checkpoint commit was recorded as `5b091d2` with scoped records-core changes.
