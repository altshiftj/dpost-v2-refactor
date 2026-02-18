# UTM Zwick end-series failure checklist

Target: address staged series key mismatch and exception extension drift documented in `docs/reports/20260216-utm_zwick_end_series_failure_report.md`

## Section: Investigation baseline
- Why this matters: keeps implementation focused on confirmed failure modes instead of assumptions.

### Checklist
- [x] Correlate upload and data folder traces for the failing sample.
- [x] Confirm exact exception stack trace and source locations.
- [x] Verify whether raw data was deleted or relocated.

### Completion Notes
- How it was done: Compared `filewatch_20260216_114326.csv`, `filewatch_20260216_114429.csv`, and `watchdog.log` around `2026-02-16 12:02`; verified raw payload moved to exceptions with wrong extension.

---

## Section: TDD failing tests (human gate)
- Why this matters: prevents regression and enforces the agreed human-in-the-loop workflow.

### Checklist
- [x] Add failing unit test for mixed-case prefix staging/lookup (`LGr-...` vs `lgr-...`).
- [x] Add failing unit test for fallback-path exception move keeping the real source extension.
- [x] Share failing test output and wait for human approval before implementation.

### Completion Notes
- How it was done: Added regression coverage for mixed-case series keys in `test_device_specific_processing_moves_staged_series` and for fallback extension drift in `test_process_item_preserves_source_extension_on_effective_path_fallback`; both initially failed with `KeyError: No staged series ...` and observed extension drift (`.xlsx` vs expected `.txt`).

---

## Section: Implementation
- Why this matters: removes the immediate production failure and prevents artefact mislabeling.

### Checklist
- [x] Normalize series key consistently in Zwick preprocessing and processing lookup paths.
- [x] Add safe fallback lookup for pre-existing in-memory keys during runtime.
- [x] Recompute prefix/extension when `effective_path` falls back to source in manager pipeline.
- [x] Ensure exception moves use accurate suffix metadata after fallback.
- [x] Keep filename sanitize/validate policy in core routing (not in file processors).

### Completion Notes
- How it was done: Updated `FileProcessorUTMZwick` to use a non-validating in-memory series key for staging/pairing only (derived from the observed stem); left filename sanitize/validate to `core.processing.routing` + rename flow. Updated `_build_candidate` in `FileProcessManager` to recompute `prefix`/`extension` when preprocessed effective path does not exist and pipeline falls back to the original source path.

---

## Section: Verification
- Why this matters: confirms bug closure under both synthetic tests and trace-replay behavior.

### Checklist
- [x] Run targeted tests:
  - `python -m pytest "tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_moves_staged_series[mixed-case-prefix]" tests/unit/core/processing/test_file_process_manager.py::test_process_item_preserves_source_extension_on_effective_path_fallback`
- [x] Run full suite:
  - `python -m pytest`
- [ ] Replay the end-series scenario and confirm no `No staged series` error and no mislabeled exceptions artefacts.

### Completion Notes
- How it was done: Verified regression tests pass with `python -m pytest "tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_moves_staged_series[mixed-case-prefix]" tests/unit/core/processing/test_file_process_manager.py::test_process_item_preserves_source_extension_on_effective_path_fallback`; also ran `python -m pytest tests/unit/device_plugins/utm_zwick/test_file_processor.py tests/unit/core/processing/test_file_process_manager.py` (21 passed), `python -m pytest tests/unit/device_plugins/utm_zwick` (6 passed), and full suite `python -m pytest` (287 passed, 4 skipped).

---

## Section: Communication
- Why this matters: gives operators and maintainers clear expectations for behavior after rollout.

### Checklist
- [ ] Post short incident summary with root cause and scope.
- [ ] Post fix summary with before/after evidence and validation commands.
- [ ] Update runbook notes if exception triage behavior changes.

### Completion Notes
- How it was done: TBD
