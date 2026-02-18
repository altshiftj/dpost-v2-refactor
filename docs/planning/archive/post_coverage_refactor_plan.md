# Post Coverage Refactor Plan

Goal: use the new coverage to safely refactor the most duplicated preprocessing and staging logic while keeping behavior stable.

## Scope Targets
- Staging + purge logic duplicated in `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py` and `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`.
- Batch reconstruction helpers duplicated in the same two processors.
- CSV/text prefix parsing helpers duplicated across PSA, Kinexus, and DSV processors.
- Minor cleanups in `src/ipat_watchdog/core/processing/*` now covered by tests.

## Phase 1: Shared Staging Utilities
- [x] Introduce a shared staging utility module (e.g. `src/ipat_watchdog/core/processing/staging_utils.py`).
  - Extract stage dir creation, stale stage dir cleanup, and batch reconstruction by stem.
- [x] Refactor PSA Horiba to use staging utilities without changing external behavior.
  - Preserve `PreprocessingResult` paths and staging folder naming (`<prefix>.__staged__N`).
- [x] Refactor Kinexus to use the same utilities.
  - Preserve native/export pairing rules and idempotent staging behavior.
- [x] Re-run PSA/Kinexus unit tests to confirm behavior parity.

## Phase 2: Shared CSV/Text Parsing Helpers
- [x] Extract text-prefix decoding into a shared helper (e.g. `core/processing/text_utils.py`).
  - Consolidate the encoding fallback loops in PSA, Kinexus, and DSV.
- [x] Replace local `_read_text_prefix` implementations in PSA/Kinexus/DSV.
  - Keep byte limits and error handling semantics unchanged.
- [x] Add/adjust tests for decoding fallbacks if needed.

## Phase 3: Batch Models and Type Hygiene
- [x] Define shared batch dataclasses for staged pairing (e.g. `core/processing/batch_models.py`).
  - Replace duplicate `_Pair`/`_FlushBatch` definitions where it improves clarity.
- [x] Tighten type hints in processors and helpers (Optional returns, explicit return types).
  - Avoid behavior changes; purely type/clarity refactors.

## Phase 4: Cleanup + Validation
- [x] Remove any dead helpers or redundant comments introduced by earlier refactors.
- [x] Run targeted tests for PSA, Kinexus, DSV, and core processing.
- [ ] Run full coverage and update `docs/planning/coverage_findings_report.md`.

## Guardrails
- Do not change file/folder naming conventions.
- Preserve staging folder semantics and idempotency.
- Keep exception/rename paths consistent with current behavior.

## Validation Checklist
- [x] `pytest tests/unit/device_plugins/psa_horiba`
- [x] `pytest tests/unit/device_plugins/rhe_kinexus`
- [x] `pytest tests/unit/device_plugins/dsv_horiba`
- [ ] `pytest --cov=src/ipat_watchdog --cov-report=term-missing`
