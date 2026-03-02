# NamingSettings Single-Source Migration Execution Checklist (2026-03-02)

## 1. Confirm Baseline and Scope
- Why this matters: locking scope up front prevents mixed migration goals and
  avoids churn across naming, storage, sync, and plugin boundaries.

### Checklist
- [x] Confirm RPC exists and is the canonical migration reference:
      `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`.
- [x] Confirm architecture cross-links are present in baseline/contract/catalog
      docs and architecture README.
- [x] Confirm this checklist tracks only naming-source and fallback-retirement
      work (not unrelated refactors).
- [x] Decide whether runtime naming-overload file/folder renames are in-scope
      for this wave or explicitly deferred.

### Completion Notes
- How it was done: kickoff baseline cross-link verification completed on
  2026-03-02 using `rg` over `docs/architecture` and `README.md`; runtime
  naming-overload renames are explicitly deferred for this wave.

---

## 2. Retire Ambient Naming Facade Lookups
- Why this matters: `current()` fallback lookups in application naming policy
  hide dependencies and weaken explicit-context guarantees.

### Checklist
- [x] Update `src/dpost/application/naming/policy.py` so naming operations use
      explicit context without ambient fallback (`_id_separator`,
      `_filename_pattern`, `_current_device` retirement path).
- [x] Update all call sites to pass explicit naming context where required
      (`id_separator`, `filename_pattern`, device metadata).
- [x] Remove or minimize compatibility wrappers once no production path depends
      on ambient reads.
- [x] Add/adjust focused tests in:
      `tests/unit/application/naming/test_policy.py`,
      `tests/unit/application/processing/test_routing_helpers.py`,
      `tests/unit/application/processing/test_file_process_manager_branches.py`,
      `tests/unit/application/records/test_record_manager.py`.

### Completion Notes
- How it was done: replaced ambient fallback behavior in
  `application/naming/policy.py` with explicit-context validation; wired
  runtime filename-pattern injection via `configure_runtime_context(...)`;
  updated Hioki modified-event checks to require injected naming context; and
  updated affected tests to pass explicit separator/pattern context.
  Validation:
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py` -> `65 passed`
  - `python -m pytest -q tests/unit/application/records/test_record_manager.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `51 passed, 1 skipped`
  - `python -m ruff check ...` (touched src/tests in this slice) -> pass

---

## 3. Remove Storage Helper Ambient Defaults
- Why this matters: storage path/separator helpers should receive explicit
  policy inputs from orchestration boundaries, not active global config.

### Checklist
- [x] Replace fallback usage in
      `src/dpost/infrastructure/storage/filesystem_utils.py` where explicit
      context is already available (`dest_dir`, `rename_dir`, `exception_dir`,
      `id_separator`, `current_device`).
- [x] Keep dependency direction intact by passing context from application or
      runtime composition boundaries only.
- [x] Remove residual `_active_config()`-based wrappers once call-site coverage
      is complete and tested.
- [x] Add/adjust focused tests in:
      `tests/unit/infrastructure/storage/test_filesystem_utils.py` and related
      processing flow tests.

### Completion Notes
- How it was done: removed ambient config wrappers from
  `infrastructure/storage/filesystem_utils.py` and made core path/persistence
  helpers fail fast unless explicit context is provided (`id_separator`,
  `dest_dir`, `base_dir`, `json_path`). Wired explicit runtime directory init
  and processor runtime context expansion from composition/manager boundaries
  so storage consumers receive context without ambient reads.
  Validation:
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `91 passed`

---

## 4. Tighten Kadi Separator Policy to Explicit Behavior
- Why this matters: separator inference in sync flows can drift from canonical
  naming policy and hides missing upstream context wiring.

### Checklist
- [x] Refactor `src/dpost/infrastructure/sync/kadi_manager.py` to rely on an
      explicit separator resolver contract rather than inference scans.
- [x] Remove or strictly constrain `_infer_id_separator_from_record(...)` and
      default fallback behavior after separator propagation is guaranteed.
- [x] Verify `LocalRecord` creation/update paths always provide separator
      information needed by sync operations.
- [x] Add/adjust tests in:
      `tests/unit/infrastructure/sync/test_sync_kadi.py` and
      `tests/unit/infrastructure/sync/test_sync_kadi_branches.py`.

### Completion Notes
- How it was done: retired separator inference/fallback behavior in
  `infrastructure/sync/kadi_manager.py`; default resolution now reads explicit
  `LocalRecord.id_separator` and raises on missing/invalid resolver output.
  Updated sync tests to validate explicit-record behavior and strict failure
  semantics.
  Validation:
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py` -> `167 passed, 1 skipped`

---

## 5. Remove Plugin Runtime Separator Fallbacks
- Why this matters: plugin-local runtime fallbacks (`current()`/`"-"`) create
  hidden behavior branches and undercut constructor/runtime context injection.

### Checklist
- [x] Update Kinexus and PSA processors to require explicit separator context
      via constructor or `configure_runtime_context(...)` before processing.
- [x] Remove `_runtime_id_separator()` fallback and `RuntimeError -> "-"` paths
      from:
      `src/dpost/device_plugins/rhe_kinexus/file_processor.py`,
      `src/dpost/device_plugins/psa_horiba/file_processor.py`.
- [x] Ensure runtime orchestration and processor factory paths always inject
      separator context before plugin processing starts.
- [x] Add/adjust focused tests in:
      `tests/unit/device_plugins/rhe_kinexus/test_file_processor.py`,
      `tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py`,
      `tests/unit/device_plugins/psa_horiba/test_file_processor.py`,
      `tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`.

### Completion Notes
- How it was done: removed Kinexus/PSA runtime separator fallback branches and
  required explicit separator context via constructor/runtime hook.
  `FileProcessManager` runtime injection now always supplies explicit naming +
  storage context to processors before plugin processing paths execute.
  Updated Kinexus/PSA/DSV/UTM branch tests for explicit-context expectations,
  including no-override behavior when explicit constructor values exist.
  Validation:
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `91 passed`

---

## 6. Naming-Clarity Renames (Follow-up Slice)
- Why this matters: naming-overload cleanup can improve readability, but it
  should not distract from explicit-context migration risk reduction.

### Checklist
- [x] If in scope, execute low-risk rename sequence from RPC:
      `application/config/runtime.py -> application/config/context.py`,
      `infrastructure/runtime/bootstrap_dependencies.py -> startup_dependencies.py`.
- [x] If out of scope, record defer decision in active report/checklist notes
      (N/A for this wave; rename slice executed in-scope).
- [x] Update imports/tests/docs consistently if rename slice is executed.

### Completion Notes
- How it was done: follow-up cleanup run executed the low-risk rename pair:
  - `src/dpost/application/config/runtime.py` ->
    `src/dpost/application/config/context.py`
  - `src/dpost/infrastructure/runtime/bootstrap_dependencies.py` ->
    `src/dpost/infrastructure/runtime/startup_dependencies.py`
  Updated imports/tests and active planning/checklist/report docs to align.
  Validation:
  - `python -m pytest -q tests/unit/application/config/test_context.py tests/unit/infrastructure/runtime/test_startup_dependencies.py tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py` -> `24 passed`

---

## 7. Remove Remaining Contract/Compatibility Seams
- Why this matters: after fallback retirement, remaining implicit constructor
  defaults and compatibility shims still hide dependency wiring intent.

### Checklist
- [x] Make rename-loop attempted-prefix composition separator-aware using
      explicit naming context.
- [x] Remove ambient session timeout lookup by requiring explicit
      `SessionManager.timeout_provider`.
- [x] Require explicit `FileProcessManager.config_service` injection and remove
      constructor global fallback.
- [x] Remove `DeviceResolution.deferred` compatibility helper and use explicit
      enum-kind checks in resolver tests/callers.

### Completion Notes
- How it was done:
  - `RenameService` now composes retry attempted prefixes with the injected
    `id_separator` context.
  - `SessionManager` now requires an explicit timeout provider and no longer
    reads ambient config via `current()`.
  - `FileProcessManager` now requires explicit `config_service` injection
    instead of `get_service()` fallback.
  - `DeviceResolution.deferred` compatibility property was removed and tests
    were updated to assert `kind is DeviceResolutionKind.DEFER`.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py -k explicit_separator_for_retry_attempt` -> failed (expected separator mismatch)
    - `python -m pytest -q tests/unit/application/session/test_session_manager.py -k requires_explicit_timeout_provider` -> failed (did not raise `TypeError`)
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k init_requires_explicit_config_service` -> failed (implicit runtime fallback path)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py tests/unit/application/session/test_session_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_device_resolver.py` -> `80 passed`
    - `python -m pytest -q tests/unit/application/config/test_context.py tests/unit/infrastructure/runtime/test_startup_dependencies.py tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py tests/unit/application/processing/test_rename_flow.py tests/unit/application/session/test_session_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_device_resolver.py` -> `104 passed`

---

## 8. Retire Record/Persistence Separator Inference Defaults
- Why this matters: record hydration and record creation should use explicit
  `NamingSettings` separator context and must not infer from identifier shape.

### Checklist
- [x] Remove `LocalRecord` identifier-shape separator inference helper and keep
      parsing explicit-context driven.
- [x] Require explicit `RecordManager.id_separator` constructor wiring and
      remove filename-prefix separator inference helper.
- [x] Require explicit `id_separator` for persisted-record hydration in:
      `filesystem_utils.load_persisted_records(...)`,
      `LocalRecord.from_dict(...)`.
- [x] Add/adjust focused tests in:
      `tests/unit/domain/records/test_local_record.py`,
      `tests/unit/application/records/test_record_manager.py`,
      `tests/unit/infrastructure/storage/test_filesystem_utils.py`.

### Completion Notes
- How it was done:
  - removed `LocalRecord` `_resolve_id_separator(...)` auto-detection path;
  - made `RecordManager` constructor explicitly require `id_separator`;
  - removed `RecordManager._infer_id_separator(...)`;
  - made persisted-record load/hydration fail fast when separator context is
    omitted.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py -k from_dict_requires_explicit_separator` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py tests/unit/application/records/test_record_manager.py tests/unit/infrastructure/storage/test_filesystem_utils.py` -> `76 passed, 1 skipped`

---

## 9. Remove Rename-Flow Separator Fallback
- Why this matters: rename retry prompts should compose attempted prefixes with
  explicit naming context only, not implicit `"-"` fallback behavior.

### Checklist
- [x] Require explicit `id_separator` in
      `RenameService.obtain_valid_prefix(...)`.
- [x] Remove separator fallback from
      `RenameService._compose_attempted_prefix(...)`.
- [x] Update focused tests in:
      `tests/unit/application/processing/test_rename_flow.py` and affected
      processing orchestration tests.

### Completion Notes
- How it was done:
  - added fail-fast separator validation to rename flow before policy calls;
  - passed validated separator through both violation analysis and retry
    attempted-prefix composition;
  - removed implicit `"-"` fallback from attempted-prefix composition helper.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py -k requires_explicit_separator` -> failed (raised filename-pattern error first)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py` -> `6 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py` -> `48 passed`

---

## 10. Remove DSV Orphan Separator Fallback
- Why this matters: plugin orphan cleanup should honor explicit runtime naming
  context and must not silently fall back to `"-"` separators.

### Checklist
- [x] Remove `FileProcessorDSVHoriba` orphan-move separator fallback.
- [x] Add explicit runtime separator resolver behavior in
      `dsv_horiba/file_processor.py`.
- [x] Update focused DSV tests for explicit runtime separator context.

### Completion Notes
- How it was done:
  - replaced `self._id_separator or "-"` in DSV orphan-move path with a strict
    runtime separator resolver;
  - kept orphan purge behavior resilient by continuing to log-and-continue when
    runtime context is missing;
  - updated DSV tests to assert explicit separator-context behavior.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py -k requires_explicit_separator_context` -> failed (orphan move still executed via fallback separator)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py` -> `12 passed`

---

## 11. Remove Error-Handling Exception-Move Fallbacks
- Why this matters: exception routing helpers should receive explicit exception
  directory + separator context and avoid hidden defaults.

### Checklist
- [x] Require explicit `exception_dir` and `id_separator` in
      `safe_move_to_exception(...)`.
- [x] Thread explicit exception context through
      `move_to_exception_and_inform(...)` and `handle_invalid_datatype(...)`.
- [x] Update focused tests in:
      `tests/unit/application/processing/test_error_handling.py` and affected
      processing/plugin tests.

### Completion Notes
- How it was done:
  - removed `safe_move_to_exception(...)` defaults for exception path and
    separator;
  - added fail-fast validation for explicit exception context;
  - updated error-handling wrapper functions to pass explicit context through
    staged/preprocessed exception-move paths.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_error_handling.py` -> failed (missing explicit-context contract and signature mismatch)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_error_handling.py` -> `6 passed`
    - `python -m pytest -q tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `69 passed`

---

## Manual Check
- Why this matters: final validation confirms fallback-retirement changes did
  not regress behavior and keeps architecture guardrails enforceable.

### Checklist
- [x] Run:
      `python -m ruff check src/dpost/application/naming/policy.py src/dpost/infrastructure/storage/filesystem_utils.py src/dpost/infrastructure/sync/kadi_manager.py src/dpost/device_plugins/rhe_kinexus/file_processor.py src/dpost/device_plugins/psa_horiba/file_processor.py tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py`
- [x] Run:
      `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py`
- [x] Run:
      `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- [x] Run:
      `rg -n "ipat_watchdog\\." src/dpost`
- [x] Confirm architecture docs remain aligned with final migration status and
      update this checklist/report pair with concrete command results.

## Completion Notes
- How it was done:
  - `python -m ruff check src/dpost/application/naming/policy.py src/dpost/infrastructure/storage/filesystem_utils.py src/dpost/infrastructure/sync/kadi_manager.py src/dpost/device_plugins/rhe_kinexus/file_processor.py src/dpost/device_plugins/psa_horiba/file_processor.py tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py` -> `All checks passed!`
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py` -> `167 passed, 1 skipped`
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `732 passed, 1 skipped, 1 warning`, `TOTAL 5385 stmts, 0 miss, 100%`
  - `python -m ruff check .` -> `All checks passed!`
  - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 8:
    - `python -m pytest -q tests/unit` -> `734 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `734 passed, 1 skipped, 1 warning`, `TOTAL 5371 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 9:
    - `python -m pytest -q tests/unit` -> `735 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `735 passed, 1 skipped, 1 warning`, `TOTAL 5377 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
  - checkpoint rerun after section 10:
    - `python -m pytest -q tests/unit` -> `736 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `736 passed, 1 skipped, 1 warning`, `TOTAL 5381 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
  - checkpoint rerun after section 11:
    - `python -m pytest -q tests/unit` -> `737 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `737 passed, 1 skipped, 1 warning`, `TOTAL 5383 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
