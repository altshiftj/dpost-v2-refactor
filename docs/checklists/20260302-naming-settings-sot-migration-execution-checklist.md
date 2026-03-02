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

## 12. Remove `get_unique_filename(...)` Separator Fallback
- Why this matters: unique-name generation is naming-policy behavior and should
  require explicit separator context instead of silently defaulting to `"-"`.

### Checklist
- [x] Make `filesystem_utils.get_unique_filename(...)` fail fast when
      `id_separator` is omitted.
- [x] Update direct call sites (plugins/tests/helpers) to pass explicit
      separator context.
- [x] Add focused storage/unit coverage for the explicit-separator contract.

### Completion Notes
- How it was done:
  - added fail-fast validation in `get_unique_filename(...)` for missing
    `id_separator`;
  - propagated explicit separators to all direct helper call sites where this
    utility is used;
  - updated affected plugin tests/mocks for explicit `id_separator` args.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py -k get_unique_filename_requires_explicit_separator` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor_branches.py tests/unit/device_plugins/test_device/test_test_device_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `111 passed`

---

## 13. Complete Runtime Adapter Folder Rename
- Why this matters: finishing the `runtime` -> `runtime_adapters` rename removes
  overloaded terminology and keeps adapter ownership obvious.

### Checklist
- [x] Rename `src/dpost/infrastructure/runtime/` to
      `src/dpost/infrastructure/runtime_adapters/`.
- [x] Update imports in source and tests to new module path.
- [x] Update active planning/checklist/report docs to reflect completion.

### Completion Notes
- How it was done:
  - renamed infrastructure adapter folder to `runtime_adapters`;
  - rewired source + test imports from
    `dpost.infrastructure.runtime.*` to
    `dpost.infrastructure.runtime_adapters.*`;
  - updated active migration docs to mark folder rename complete.
  Validation:
  - `python -m pytest -q tests/unit/infrastructure/runtime tests/unit/runtime tests/unit/application/runtime` -> `125 passed, 1 warning`
  - `python -m ruff check src/dpost/application/runtime/device_watchdog_app.py src/dpost/runtime/bootstrap.py src/dpost/runtime/composition.py src/dpost/infrastructure/runtime_adapters tests/unit/infrastructure/runtime/test_dialogs.py tests/unit/infrastructure/runtime/test_headless_ui.py tests/unit/infrastructure/runtime/test_startup_dependencies.py tests/unit/infrastructure/runtime/test_ui_adapters.py tests/unit/infrastructure/runtime/test_ui_factory.py tests/unit/infrastructure/runtime/test_ui_tkinter.py` -> `All checks passed!`

---

## 14. Post-Checklist Explicit-Context Cleanup
- Why this matters: even after fallback retirement, hardcoded separator usage
  and stale runtime-path docs can quietly reintroduce naming drift and
  contributor confusion.

### Checklist
- [x] Replace hardcoded plugin `id_separator="-"` usage in unique-name
      generation with runtime separator context.
- [x] Tighten Kadi sync helper seams so separator context is forwarded
      explicitly through helper calls.
- [x] Align architecture docs to `runtime_adapters` path naming and update
      stale `NamingSettings` docstring wording.

### Completion Notes
- How it was done:
  - updated plugin processors to use injected runtime `id_separator` for
    `get_unique_filename(...)` calls (Hioki, DSV, Kinexus, UTM, SEM, EXTR,
    EIRICH EL1/R01, test-device processor);
  - tightened Kadi `_prepare_resources(...)` to forward explicit separator to
    user-lookup helper and updated helper signatures to require explicit
    separator context;
  - updated architecture baseline/contract/responsibility catalog references
    from `infrastructure/runtime` to `infrastructure/runtime_adapters`, and
    refreshed stale `NamingSettings` docstring language.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_processing_uses_configured_separator_for_unique_filename tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_moves_staged_series` -> failed (hardcoded separator persisted)
    - `python -m pytest -q tests/unit/infrastructure/sync/test_sync_kadi_branches.py::test_prepare_resources_threads_separator_across_resource_builders` -> failed (separator not forwarded to user helper seam)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/erm_hioki tests/unit/device_plugins/utm_zwick tests/unit/device_plugins/dsv_horiba tests/unit/device_plugins/sem_phenomxl2 tests/unit/device_plugins/extr_haake tests/unit/device_plugins/test_device tests/unit/device_plugins/rhe_kinexus` -> `79 passed`
    - `python -m pytest -q tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py` -> `31 passed`

---

## 15. Remove Plugin Exception-Dir Parent Fallbacks
- Why this matters: stale-artifact exception moves should use explicit runtime
  exception routing context instead of implicit `path.parent` fallback paths.

### Checklist
- [x] Remove `path.parent` fallback in Kinexus stale move paths and require
      explicit runtime `exception_dir` context.
- [x] Remove `path.parent` fallback in PSA stale move paths and require
      explicit runtime `exception_dir` context.
- [x] Remove `path.parent` fallback in DSV orphan purge path and require
      explicit runtime `exception_dir` context.
- [x] Update focused plugin tests to pass explicit exception-dir context where
      stale move calls are expected and add coverage for missing exception-dir
      no-op behavior.

### Completion Notes
- How it was done:
  - replaced Kinexus/PSA/DSV stale-move exception-dir parent fallbacks with
    strict runtime exception-dir resolvers;
  - added explicit missing-exception-dir branch tests that assert stale-move
    helpers are skipped when exception-dir context is not configured;
  - updated stale-move success/failure tests to inject explicit
    `exception_dir` context where move calls are expected.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py::test_purge_orphans_requires_explicit_exception_dir_context tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context` -> failed (fallback still moved items)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py::test_purge_orphans_requires_explicit_exception_dir_context tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py::test_purge_orphans_moves_files tests/unit/device_plugins/rhe_kinexus/test_file_processor.py::test_purge_stale_moves_pending_bucket_sentinel_and_stage tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_covers_exception_and_cleanup_paths tests/unit/device_plugins/psa_horiba/test_purge_and_reconstruct.py::test_purge_stale_moves_pending_bucket_sentinel_and_stage tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_covers_exception_paths` -> `8 passed`
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba tests/unit/device_plugins/rhe_kinexus tests/unit/device_plugins/psa_horiba` -> `71 passed`

---

## 16. Retire Remaining Plugin Separator Fallback Resolvers
- Why this matters: lingering plugin-local `self._id_separator or "-"` helpers
  kept implicit naming behavior alive in direct plugin execution paths.

### Checklist
- [x] Remove fallback resolver behavior from remaining plugin processors:
      `extr_haake`, `sem_phenomxl2`, `test_device`,
      `rmx_eirich_el1`, `rmx_eirich_r01`, `erm_hioki`, `utm_zwick`.
- [x] Require explicit runtime separator context in those processors and fail
      fast when context was not configured.
- [x] Update focused plugin tests so happy paths inject explicit runtime
      separator context, and add missing-context branch coverage.

### Completion Notes
- How it was done:
  - replaced plugin-local fallback resolvers with strict
    `_resolve_id_separator(...)` methods that raise when runtime separator
    context is missing;
  - updated affected plugin happy-path tests to call
    `configure_runtime_context(id_separator=...)` before processing;
  - added focused missing-context tests for EXTR, SEM, test-device, Eirich
    EL1/R01, Hioki, and UTM processing paths.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/extr_haake/test_plugin.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py::test_device_specific_processing_requires_explicit_separator_context tests/unit/device_plugins/test_device/test_test_device_file_processor.py::test_test_device_processor_requires_explicit_separator_context tests/unit/device_plugins/mix_eirich/test_file_processor.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_requires_explicit_separator_context` -> `7 failed` (fallback still processed with implicit separator)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/extr_haake tests/unit/device_plugins/sem_phenomxl2 tests/unit/device_plugins/test_device tests/unit/device_plugins/mix_eirich tests/unit/device_plugins/erm_hioki tests/unit/device_plugins/utm_zwick` -> `62 passed`
    - `python -m ruff check src/dpost/device_plugins/erm_hioki/file_processor.py src/dpost/device_plugins/extr_haake/file_processor.py src/dpost/device_plugins/rmx_eirich_el1/file_processor.py src/dpost/device_plugins/rmx_eirich_r01/file_processor.py src/dpost/device_plugins/sem_phenomxl2/file_processor.py src/dpost/device_plugins/test_device/file_processor.py src/dpost/device_plugins/utm_zwick/file_processor.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/erm_hioki/test_file_processor_branches.py tests/unit/device_plugins/extr_haake/test_plugin.py tests/unit/device_plugins/mix_eirich/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor_branches.py tests/unit/device_plugins/test_device/test_test_device_file_processor.py tests/unit/device_plugins/utm_zwick/test_file_processor.py` -> `All checks passed!`

---

## 17. Remove `LocalRecord` Empty-Separator Fallback
- Why this matters: `LocalRecord.__post_init__` still coerced empty separator
  values to `"-"`, which allowed implicit naming policy in a core domain path.

### Checklist
- [x] Remove `LocalRecord` post-init fallback from empty separator to default.
- [x] Fail fast when `LocalRecord` is constructed with empty separator context.
- [x] Add focused unit coverage for missing-separator construction.

### Completion Notes
- How it was done:
  - updated `LocalRecord.__post_init__` to require non-empty
    `id_separator` context instead of coercing to `"-"`;
  - added targeted test coverage for empty-separator construction failure.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py::test_init_rejects_empty_separator_value` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py tests/unit/application/records/test_record_manager.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/storage/test_filesystem_utils.py` -> `90 passed, 1 skipped`
    - `python -m ruff check src/dpost/domain/records/local_record.py tests/unit/domain/records/test_local_record.py` -> `All checks passed!`

---

## 18. Tighten UTM Flush Runtime-Context Contract
- Why this matters: `flush_incomplete()` silently skipped staged flush work
  when runtime context was missing, which hid wiring errors in deferred
  processing paths.

### Checklist
- [x] Remove silent missing-context skip behavior from UTM flush path.
- [x] Require explicit runtime `id_separator` and `dest_dir` context during
      flush execution.
- [x] Add focused branch tests for missing-context failure and configured
      flush success.

### Completion Notes
- How it was done:
  - updated UTM flush execution to resolve runtime separator/destination
    context explicitly before per-series processing;
  - removed silent skip logging branch for missing runtime context;
  - added focused tests covering explicit missing-context error and configured
    staged flush behavior.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py -k "flush_incomplete_requires_explicit_separator_context or flush_incomplete_processes_staged_series_with_runtime_context"` -> failed (flush silently skipped missing-context series)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py -k "flush_incomplete_requires_explicit_separator_context or flush_incomplete_processes_staged_series_with_runtime_context"` -> `2 passed, 6 deselected`
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick` -> `17 passed`

---

## 19. Narrow Package-Level Config Context Exports
- Why this matters: exporting ambient service helpers from
  `dpost.application.config` makes deep `current()` usage easy to reintroduce
  outside composition-focused boundaries.

### Checklist
- [x] Remove package-level re-exports of `current`, `get_service`, and
      `set_service` from `dpost.application.config`.
- [x] Update test imports to use `dpost.application.config.context` for ambient
      helper access where needed.
- [x] Add namespace guard coverage to prevent reintroducing package-level
      ambient helper exports.

### Completion Notes
- How it was done:
  - narrowed `dpost.application.config` exports to omit ambient helper symbols
    (`current`, `get_service`, `set_service`);
  - updated tests that intentionally use ambient context helpers to import
    `current` from `dpost.application.config.context`;
  - added a focused namespace-guard unit test.
  Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py::test_config_package_namespace_omits_ambient_service_helpers` -> failed (`current` remained exported at package level)
  - green-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py tests/integration/test_settings_integration.py` -> `6 passed`
    - `python -m pytest -q tests/unit/device_plugins/extr_haake/test_plugin.py` -> `5 passed`

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
  - checkpoint rerun after sections 12-13:
    - `python -m pytest -q tests/unit` -> `738 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `738 passed, 1 skipped, 1 warning`, `TOTAL 5385 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 16:
    - `python -m pytest -q tests/unit` -> `754 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `754 passed, 1 skipped, 1 warning`, `TOTAL 5446 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 17:
    - `python -m pytest -q tests/unit` -> `755 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `755 passed, 1 skipped, 1 warning`, `TOTAL 5447 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 18:
    - `python -m pytest -q tests/unit` -> `758 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `758 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
  - checkpoint rerun after section 19:
    - `python -m pytest -q tests/unit` -> `759 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `759 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches
