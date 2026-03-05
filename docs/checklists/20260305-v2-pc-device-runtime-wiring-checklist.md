# Checklist: V2 PC/Device Runtime Wiring

## Section: Baseline lock
- Why this matters: Freeze known-good startup and plugin-contract behavior before runtime wiring.

### Checklist
- [ ] Confirm branch is `rewrite/v2-manual-pc-device-bringup` and working tree is clean.
- [ ] Re-run manual bring-up baseline from [20260305-v2-manual-pc-device-bringup-checklist.md](d:/Repos/d-post/docs/checklists/20260305-v2-manual-pc-device-bringup-checklist.md).
- [ ] Capture baseline command outputs in this checklist completion notes.

### Completion Notes
- How it was done:

---

## Section: Runtime execution contract (TDD)
- Why this matters: Prevent regression where startup succeeds but runtime ingestion never runs.

### Checklist
- [x] Add failing tests for non-dry-run runtime execution path in `tests/dpost_v2/test___main__.py`.
- [x] Add failing tests for dry-run path to confirm runtime loop is not executed.
- [x] Implement minimal entry/bootstrap wiring changes to make tests pass.

### Completion Notes
- How it was done:
  - Added new tests in `tests/dpost_v2/test___main__.py` for:
    - non-dry-run calls `runtime_handle.run()` once,
    - dry-run does not call runtime,
    - missing `run()` fails fast,
    - missing `terminal_reason` fails fast,
    - runtime exception exits with code `1`,
    - runtime terminal mapping:
      - `end_of_stream|cancelled|soft_timeout -> 0`
      - `failed_terminal|hard_timeout -> 1`.
  - Updated existing success-path tests to invoke `--dry-run` where startup-only success is expected.
  - Implemented runtime execution contract in `src/dpost_v2/__main__.py`:
    - non-dry-run executes runtime handle,
    - validates runtime handle/result shape,
    - maps exit codes from runtime terminal reason,
    - prints success message only after runtime success for non-dry-run.
  - Validation run:
    - `python -m pytest -q tests/dpost_v2/test___main__.py` -> `22 passed`
    - `python -m ruff check src/dpost_v2 tests/dpost_v2` -> passed.

---

## Section: Real ingestion engine composition
- Why this matters: Replace noop runtime behavior with real staged ingestion execution.

### Checklist
- [x] Add failing composition/runtime tests proving real ingestion engine wiring is used.
- [x] Implement minimal changes in `src/dpost_v2/runtime/composition.py` to compose real ingestion engine and handlers.
- [x] Keep stage boundaries and contract validation stable while making tests pass.
- [x] Ensure composition preserves responsibility split: PC plugin sets workstation/device scope; sync backend handles outbound transport.

### Completion Notes
- How it was done:
  - Added failing proof test in `tests/dpost_v2/runtime/test_composition.py`:
    - `test_composition_default_app_uses_real_ingestion_engine_pipeline`
    - Expected `final_stage_id == "post_persist"` (failed under noop engine, passed after wiring).
  - Replaced default noop engine wiring in `src/dpost_v2/runtime/composition.py` with:
    - a real `IngestionEngine` + `PipelineRunner(DEFAULT_INGESTION_TRANSITION_TABLE)`,
    - concrete stage handlers for resolve/stabilize/route/persist/post_persist,
    - runtime adapter to enforce `IngestionState.from_event` initialization.
  - Preserved responsibility split in composition logic:
    - plugin host used for device scope/selection,
    - sync backend used for transport invocation via `sync_record`.
  - Validation runs:
    - `python -m pytest -q tests/dpost_v2/runtime/test_composition.py` -> `11 passed`
    - `python -m pytest -q tests/dpost_v2/runtime tests/dpost_v2/application/runtime` -> `24 passed`
    - `python -m pytest -q tests/dpost_v2/application/ingestion` -> `49 passed`
    - `python -m ruff check src/dpost_v2 tests/dpost_v2` -> passed.

---

## Section: Deterministic headless event source
- Why this matters: Manual runtime verification requires predictable non-UI input behavior.

### Checklist
- [x] Add failing runtime tests for deterministic headless event-source handling.
- [x] Implement minimal event-source wiring to process at least one deterministic event/file path.
- [x] Verify non-dry-run headless mode processes expected input and exits deterministically.

### Completion Notes
- How it was done:
  - Added failing test in `tests/dpost_v2/runtime/test_composition.py`:
    - `test_composition_headless_fallback_event_source_scans_watch_dir`
    - Initial failure showed `processed_count == 0` because no fallback event source existed.
  - Implemented deterministic headless fallback in `src/dpost_v2/runtime/composition.py`:
    - when UI adapter has no `iter_events`, scan `settings.paths.watch`,
    - emit sorted file events with deterministic `event_id` hashing,
    - feed these events into runtime app for processing.
  - Validation run:
    - `python -m pytest -q tests/dpost_v2/runtime/test_composition.py::test_composition_headless_fallback_event_source_scans_watch_dir` -> passed
    - broader targeted runtime/app/ingestion suites also passed (see validation section).

---

## Section: Plugin pair processing proof
- Why this matters: Confirms runtime can execute a concrete device/PC pair path, not only startup contracts.

### Checklist
- [x] Validate runtime path with `horiba_blb` as workstation policy owner for allowed devices.
- [x] Validate runtime path with `psa_horiba` device plugin through processor `prepare/can_process/process` under that PC scope.
- [x] Validate PC payload-shaping behavior independently from sync transport backend behavior.
- [x] Record final manual command outputs and artifact effects (processed path, emitted payloads, sync backend behavior).

### Completion Notes
- How it was done:
  - Executed a scoped runtime proof script with:
    - plugin profile activation restricted to `{'horiba_blb', 'psa_horiba'}`,
    - headless watch dir containing `horiba_sample.ngb`,
    - runtime composed with real ingestion engine.
  - Observed results:
    - `selected_devices=('psa_horiba',)`,
    - `selected_pcs=('horiba_blb',)`,
    - runtime processed one file successfully (`terminal_reason='end_of_stream'`),
    - engine outcome reached `final_stage_id='post_persist'`,
    - candidate resolved to `plugin_id='psa_horiba'`,
    - PC payload shaping confirmed via `horiba_blb` `create_sync_adapter` and `prepare_sync_payload`,
    - emitted runtime event kinds: `runtime_started`, `runtime_event_processed`, `ingestion_succeeded`, `runtime_completed`.

---

## Section: Validation gates and closeout
- Why this matters: Ensures runtime wiring is stable and ready for broader stabilization work.

### Checklist
- [x] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [x] Run targeted suites: `tests/dpost_v2/test___main__.py`, `tests/dpost_v2/runtime`, `tests/dpost_v2/application/runtime`, `tests/dpost_v2/application/ingestion`, and plugin integration tests.
- [x] Run `python -m pytest -q tests/dpost_v2` and document final status, risks, and deferred items.

### Completion Notes
- How it was done:
  - Completed:
    - `python -m pytest -q tests/dpost_v2/test___main__.py` -> `22 passed`
    - `python -m ruff check src/dpost_v2 tests/dpost_v2` -> passed.
    - `python -m pytest -q tests/dpost_v2/runtime tests/dpost_v2/application/runtime tests/dpost_v2/application/ingestion tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/plugins/test_host.py` -> `107 passed`
    - `python -m pytest -q tests/dpost_v2` -> `391 passed`
  - Remaining:
    - baseline-lock section still references a clean-tree precondition from before this implementation slice.
