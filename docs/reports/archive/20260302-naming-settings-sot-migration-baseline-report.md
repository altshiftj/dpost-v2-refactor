# NamingSettings Single-Source Migration Baseline Report (2026-03-02)

## Title
- Baseline findings and execution order for completing the NamingSettings
  single-source-of-truth migration.

## Date
- 2026-03-02

## Context
- The project already aligned on `NamingSettings` as the canonical naming
  policy owner in `src/dpost/application/config/schema.py`.
- The migration intent and historical rationale were documented in:
  `docs/planning/archive/20260224-naming-settings-single-source-of-truth-rpc.md`.
- Architecture docs now cross-link that RPC, but residual compatibility seams
  remain in naming/storage/sync/plugin paths.

## Findings

### 1. Decision alignment is complete at the documentation level
- The architecture docs and README now explicitly point to the RPC.
- This gives one canonical decision record for separator/pattern ownership and
  migration direction.

### 2. Application naming facade still contains ambient runtime lookups
- `src/dpost/application/naming/policy.py` still resolves naming behavior via
  `current()` fallback wrappers (`_id_separator`, `_filename_pattern`,
  `_current_device`) when explicit context is not passed.
- This remains the main application-layer compatibility seam.

### 3. Storage helpers still retain ambient compatibility wrappers
- `src/dpost/infrastructure/storage/filesystem_utils.py` still includes
  `_active_config()` wrappers for paths/separator defaults.
- Most hot paths now pass explicit context, but fallback behavior remains
  available and can still mask missing wiring in call sites.

### 4. Sync layer still supports separator inference/fallback behavior
- `src/dpost/infrastructure/sync/kadi_manager.py` retains
  `_infer_id_separator_from_record(...)` and default/fallback separator logic.
- This is compatible today, but it prevents a strict explicit-context posture.

### 5. Kinexus/PSA processors still have runtime separator fallback
- `src/dpost/device_plugins/rhe_kinexus/file_processor.py` and
  `src/dpost/device_plugins/psa_horiba/file_processor.py` still include
  `_runtime_id_separator()` (`current()` read) and a final `"-"` fallback on
  runtime errors.
- `configure_runtime_context(...)` injection exists, so this is now a cleanup
  seam rather than a missing capability.

### 6. Core processing path is mostly prepared for final cleanup
- Existing slices already wired explicit separator/pattern/path context through
  key processing, rename, record, and storage flows.
- Remaining work is mainly retirement of compatibility wrappers and fallback
  policies, not broad architecture redesign.

## Evidence
- Decision and migration plan:
  - `docs/planning/archive/20260224-naming-settings-single-source-of-truth-rpc.md`
- Architecture cross-links:
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/architecture-baseline.md`
  - `docs/architecture/responsibility-catalog.md`
  - `docs/architecture/README.md`
- Residual ambient/fallback seams:
  - `src/dpost/application/naming/policy.py`
  - `src/dpost/infrastructure/storage/filesystem_utils.py`
  - `src/dpost/infrastructure/sync/kadi_manager.py`
  - `src/dpost/device_plugins/rhe_kinexus/file_processor.py`
  - `src/dpost/device_plugins/psa_horiba/file_processor.py`
- Baseline verification command outputs (2026-03-02 local run):
  - `rg -n "current\\(\\)\\.(id_separator|filename_pattern|sample_name_pattern)" src/dpost`
  - `rg -n "def _id_separator_for_record|configure_runtime_context\\(" src/dpost`
  - `rg -n "move_to_exception_folder|move_to_rename_folder|get_record_path\\(" src/dpost`

## Risks
- Removing fallback behavior too early can break direct plugin construction and
  non-runtime test fixtures.
- Partial migration of naming/storage helpers can create mixed explicit/ambient
  behavior that is hard to reason about.
- Kadi separator inference removal without guaranteed record-level separator
  availability could cause identifier drift in sync artifacts.
- Runtime naming-overload renames (`runtime.py`/runtime folder naming) add
  churn; they should stay explicitly scoped as optional/deferred unless bundled
  with related refactors.

## Recommended Execution Order
1. Retire ambient `current()` naming reads in `application/naming/policy.py`
   after verifying all call sites already pass explicit context.
2. Remove ambient config defaults from `filesystem_utils.py` where explicit
   context is already available in application/runtime boundaries.
3. Tighten Kadi separator policy to explicit resolver behavior and remove
   inference fallback once record separator propagation is guaranteed.
4. Remove Kinexus/PSA runtime separator fallback (`current()` + `"-"` fallback)
   and keep only explicit constructor/runtime injection paths.
5. Run full checkpoint (`ruff`, targeted pytest, full unit coverage run) and
   document results in this report/checklist set.

## Open Questions
- Should runtime naming-overload renames in the RPC (for clarity only) be part
  of this migration wave?
  - Answer: Default to deferred unless it unblocks active seam removal.
- Do we keep any compatibility fallback wrappers for one final release window?
  - Answer: Prefer full removal in active paths; if retained, keep clearly
    marked and scope-limited with explicit retirement criteria.

## Progress Update: Section 2 Completed (2026-03-02)
- Intended action:
  - remove ambient naming lookups from `application/naming/policy.py` and move
    runtime callers to explicit naming context.
- Observed outcome:
  - retired `current()` fallback reads from policy facade;
  - switched facade APIs to explicit separator/pattern validation;
  - extended processor runtime-context hook with `filename_pattern`;
  - updated manager runtime context injection and Hioki modified-event behavior
    to rely on injected naming context;
  - updated focused tests for explicit-context expectations.
- Validation:
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py` -> `65 passed`
  - `python -m pytest -q tests/unit/application/records/test_record_manager.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `51 passed, 1 skipped`
  - `python -m ruff check ...` (changed files in this slice) -> pass

## Progress Update: Sections 3-5 Completed (2026-03-02)
- Intended actions:
  - remove ambient storage defaults from `filesystem_utils.py`,
  - tighten Kadi separator policy to explicit resolver behavior,
  - remove Kinexus/PSA runtime separator fallbacks.
- Observed outcome:
  - storage helpers now require explicit context for record/rename/exception
    paths and persisted-record JSON paths (`id_separator`, `dest_dir`,
    `base_dir`, `json_path`) with fail-fast validation;
  - runtime/composition boundaries now inject explicit naming + storage context
    (`id_separator`, `filename_pattern`, `dest_dir`, `rename_dir`,
    `exception_dir`, `current_device`) into processor runtime hooks;
  - Kadi sync no longer infers separator from record identifier patterns and
    now enforces explicit/valid separator resolver outputs;
  - Kinexus/PSA processor fallback separator logic was retired; separator usage
    now depends on explicit constructor/runtime injection;
  - DSV/UTM runtime context hooks were aligned to explicit runtime context
    propagation and covered in branch tests.
- Validation:
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `91 passed`
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py` -> `167 passed, 1 skipped`
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `729 passed, 1 skipped, 1 warning`, `TOTAL 5391 stmts, 0 miss, 100%`
  - `python -m ruff check .` -> `All checks passed!`
  - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Follow-up Cleanup Run (2026-03-02)
- Intended actions:
  - execute deferred low-risk naming-clarity renames,
  - remove remaining constructor/runtime compatibility seams in
    rename/session/processing/resolver paths.
- Observed outcome:
  - renamed runtime-overloaded modules:
    - `application/config/runtime.py` -> `application/config/context.py`
    - `infrastructure/runtime/bootstrap_dependencies.py` ->
      `infrastructure/runtime/startup_dependencies.py`
  - updated package/runtime/test imports to new module names;
  - made rename retry attempted-prefix composition separator-aware using
    explicit `id_separator`;
  - removed ambient `current()` fallback from `SessionManager` by requiring an
    explicit timeout-provider dependency;
  - removed `FileProcessManager` implicit `get_service()` fallback and required
    explicit `config_service`;
  - removed `DeviceResolution.deferred` compatibility helper and standardized
    on explicit `DeviceResolutionKind` checks in tests.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py -k explicit_separator_for_retry_attempt` -> failed (expected separator mismatch)
    - `python -m pytest -q tests/unit/application/session/test_session_manager.py -k requires_explicit_timeout_provider` -> failed (did not raise `TypeError`)
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k init_requires_explicit_config_service` -> failed (implicit config fallback path)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py tests/unit/application/session/test_session_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_device_resolver.py` -> `80 passed`
    - `python -m pytest -q tests/unit/application/config/test_context.py tests/unit/infrastructure/runtime/test_startup_dependencies.py tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py tests/unit/application/processing/test_rename_flow.py tests/unit/application/session/test_session_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_device_resolver.py` -> `104 passed`
    - `python -m ruff check .` -> `All checks passed!`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `732 passed, 1 skipped, 1 warning`, `TOTAL 5385 stmts, 0 miss, 100%`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 8 Record/Persistence Explicit Separator Contracts (2026-03-02)
- Intended actions:
  - remove remaining record/persistence separator inference defaults.
- Observed outcome:
  - removed identifier-shape separator inference from
    `domain/records/local_record.py`;
  - required explicit `RecordManager.id_separator` constructor wiring and
    removed filename-prefix separator inference from
    `application/records/record_manager.py`;
  - required explicit separator context in persisted-record hydration:
    `infrastructure/storage/filesystem_utils.load_persisted_records(...)` and
    `LocalRecord.from_dict(...)`.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py -k from_dict_requires_explicit_separator` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py tests/unit/application/records/test_record_manager.py tests/unit/infrastructure/storage/test_filesystem_utils.py` -> `76 passed, 1 skipped`
    - `python -m pytest -q tests/unit` -> `734 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `734 passed, 1 skipped, 1 warning`, `TOTAL 5371 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 9 Rename-Flow Separator Fallback Removal (2026-03-02)
- Intended actions:
  - remove retry attempted-prefix separator fallback in rename flow.
- Observed outcome:
  - `RenameService.obtain_valid_prefix(...)` now fail-fast validates explicit
    separator context before invoking naming-policy helpers;
  - `RenameService._compose_attempted_prefix(...)` now composes with the
    validated explicit separator and no longer defaults to `"-"`.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py -k requires_explicit_separator` -> failed (raised filename-pattern error first)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_rename_flow.py` -> `6 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py` -> `48 passed`
    - `python -m pytest -q tests/unit` -> `735 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `735 passed, 1 skipped, 1 warning`, `TOTAL 5377 stmts, 0 miss, 100%`
    - `python -m ruff check src/dpost/application/processing/rename_flow.py tests/unit/application/processing/test_rename_flow.py` -> `All checks passed!`

## Progress Update: Section 10 DSV Orphan Separator Fallback Removal (2026-03-02)
- Intended actions:
  - remove DSV plugin orphan-move `"-"` separator fallback.
- Observed outcome:
  - replaced DSV orphan-move separator fallback with strict runtime separator
    resolution in `device_plugins/dsv_horiba/file_processor.py`;
  - updated DSV unit tests so orphan-move success/failure scenarios pass
    explicit runtime separator context;
  - added explicit test coverage that missing runtime separator context no
    longer triggers orphan-move calls.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py -k requires_explicit_separator_context` -> failed (orphan move still executed via fallback separator)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py` -> `12 passed`
    - `python -m pytest -q tests/unit` -> `736 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `736 passed, 1 skipped, 1 warning`, `TOTAL 5381 stmts, 0 miss, 100%`
    - `python -m ruff check src/dpost/device_plugins/dsv_horiba/file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py` -> `All checks passed!`

## Progress Update: Section 11 Error-Handling Exception-Move Fallback Removal (2026-03-02)
- Intended actions:
  - remove implicit exception path/separator defaults from error-handling
    helpers.
- Observed outcome:
  - `safe_move_to_exception(...)` now requires explicit `exception_dir` and
    `id_separator` context;
  - `move_to_exception_and_inform(...)` and `handle_invalid_datatype(...)`
    now forward explicit exception context through all exception-move paths;
  - updated error-handling tests and affected processing/plugin coverage for
    explicit-context behavior.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_error_handling.py` -> failed (missing explicit-context contract and signature mismatch)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_error_handling.py` -> `6 passed`
    - `python -m pytest -q tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `69 passed`
    - `python -m pytest -q tests/unit` -> `737 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `737 passed, 1 skipped, 1 warning`, `TOTAL 5383 stmts, 0 miss, 100%`
    - `python -m ruff check src/dpost/application/processing/error_handling.py tests/unit/application/processing/test_error_handling.py` -> `All checks passed!`

## Progress Update: Section 12 `get_unique_filename(...)` Fallback Removal (2026-03-02)
- Intended actions:
  - remove implicit `"-"` separator fallback from storage unique-name helper.
- Observed outcome:
  - `filesystem_utils.get_unique_filename(...)` now requires explicit
    `id_separator` context;
  - updated direct utility call sites in plugins/tests to pass explicit
    separator arguments;
  - expanded storage test coverage for missing-separator fail-fast behavior.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py -k get_unique_filename_requires_explicit_separator` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor_branches.py tests/unit/device_plugins/test_device/test_test_device_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `111 passed`

## Progress Update: Section 13 Runtime Adapter Folder Rename Completion (2026-03-02)
- Intended actions:
  - complete deferred high-churn runtime adapter folder rename.
- Observed outcome:
  - renamed `src/dpost/infrastructure/runtime/` to
    `src/dpost/infrastructure/runtime_adapters/`;
  - updated source/test import paths from
    `dpost.infrastructure.runtime.*` to
    `dpost.infrastructure.runtime_adapters.*`;
  - aligned active migration docs with completed rename state.
- Validation:
  - `python -m pytest -q tests/unit/infrastructure/runtime tests/unit/runtime tests/unit/application/runtime` -> `125 passed, 1 warning`
  - `python -m ruff check src/dpost/application/runtime/device_watchdog_app.py src/dpost/runtime/bootstrap.py src/dpost/runtime/composition.py src/dpost/infrastructure/runtime_adapters tests/unit/infrastructure/runtime/test_dialogs.py tests/unit/infrastructure/runtime/test_headless_ui.py tests/unit/infrastructure/runtime/test_startup_dependencies.py tests/unit/infrastructure/runtime/test_ui_adapters.py tests/unit/infrastructure/runtime/test_ui_factory.py tests/unit/infrastructure/runtime/test_ui_tkinter.py` -> `All checks passed!`
  - `python -m pytest -q tests/unit` -> `738 passed, 1 skipped, 1 warning`
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `738 passed, 1 skipped, 1 warning`, `TOTAL 5385 stmts, 0 miss, 100%`
  - `python -m ruff check .` -> `All checks passed!`
  - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 14 Post-Checklist Explicit-Context Cleanup (2026-03-02)
- Intended actions:
  - remove residual hardcoded plugin separator usage in unique-name generation,
  - tighten Kadi sync separator forwarding seams,
  - align architecture/runtime path docs and stale naming docstrings.
- Observed outcome:
  - plugin processors now pass runtime separator context to
    `get_unique_filename(...)` instead of hardcoded `"-"` values;
  - Kadi `_prepare_resources(...)` now forwards explicit separator context into
    user lookup helper wiring and related helper signatures require explicit
    separator values;
  - architecture baseline/contract/responsibility docs were aligned to
    `runtime_adapters` naming;
  - stale `NamingSettings` docstring wording referencing legacy constants was
    removed.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_processing_uses_configured_separator_for_unique_filename tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_moves_staged_series` -> failed (hardcoded separator paths)
    - `python -m pytest -q tests/unit/infrastructure/sync/test_sync_kadi_branches.py::test_prepare_resources_threads_separator_across_resource_builders` -> failed (separator not forwarded through helper seam)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/erm_hioki tests/unit/device_plugins/utm_zwick tests/unit/device_plugins/dsv_horiba tests/unit/device_plugins/sem_phenomxl2 tests/unit/device_plugins/extr_haake tests/unit/device_plugins/test_device tests/unit/device_plugins/rhe_kinexus` -> `79 passed`
    - `python -m pytest -q tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py` -> `31 passed`

## Progress Update: Section 15 Plugin Exception-Dir Parent Fallback Removal (2026-03-02)
- Intended actions:
  - remove plugin-local stale-move exception-dir parent fallback behavior.
- Observed outcome:
  - DSV, Kinexus, and PSA stale exception-move paths now require explicit
    runtime exception-dir context;
  - stale-move helper tests now cover missing exception-dir no-op behavior;
  - stale-move success/failure tests now inject explicit exception-dir context
    in line with runtime composition contracts.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py::test_purge_orphans_requires_explicit_exception_dir_context tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context` -> failed (fallback still moved stale artefacts)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py::test_purge_orphans_requires_explicit_exception_dir_context tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_requires_exception_dir_context tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py::test_purge_orphans_moves_files tests/unit/device_plugins/rhe_kinexus/test_file_processor.py::test_purge_stale_moves_pending_bucket_sentinel_and_stage tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py::test_purge_stale_covers_exception_and_cleanup_paths tests/unit/device_plugins/psa_horiba/test_purge_and_reconstruct.py::test_purge_stale_moves_pending_bucket_sentinel_and_stage tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py::test_purge_stale_covers_exception_paths` -> `8 passed`
    - `python -m pytest -q tests/unit/device_plugins/dsv_horiba tests/unit/device_plugins/rhe_kinexus tests/unit/device_plugins/psa_horiba` -> `71 passed`

## Progress Update: Section 16 Remaining Plugin Separator Fallback Retirement (2026-03-02)
- Intended actions:
  - remove remaining plugin-local `self._id_separator or "-"` fallback
    resolver behavior.
- Observed outcome:
  - strict runtime separator resolver methods now back remaining plugin
    processors (`extr_haake`, `sem_phenomxl2`, `test_device`,
    `rmx_eirich_el1`, `rmx_eirich_r01`, `erm_hioki`, `utm_zwick`);
  - plugin processing now fails fast when separator context was not configured
    instead of silently using `"-"`;
  - updated plugin tests inject explicit runtime separator context on happy
    paths and cover missing-context failure branches.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/extr_haake/test_plugin.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py::test_device_specific_processing_requires_explicit_separator_context tests/unit/device_plugins/test_device/test_test_device_file_processor.py::test_test_device_processor_requires_explicit_separator_context tests/unit/device_plugins/mix_eirich/test_file_processor.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_processing_requires_explicit_separator_context tests/unit/device_plugins/utm_zwick/test_file_processor.py::test_device_specific_processing_requires_explicit_separator_context` -> `7 failed` (fallback still processed without explicit context)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/extr_haake tests/unit/device_plugins/sem_phenomxl2 tests/unit/device_plugins/test_device tests/unit/device_plugins/mix_eirich tests/unit/device_plugins/erm_hioki tests/unit/device_plugins/utm_zwick` -> `62 passed`
    - `python -m ruff check src/dpost/device_plugins/erm_hioki/file_processor.py src/dpost/device_plugins/extr_haake/file_processor.py src/dpost/device_plugins/rmx_eirich_el1/file_processor.py src/dpost/device_plugins/rmx_eirich_r01/file_processor.py src/dpost/device_plugins/sem_phenomxl2/file_processor.py src/dpost/device_plugins/test_device/file_processor.py src/dpost/device_plugins/utm_zwick/file_processor.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/erm_hioki/test_file_processor_branches.py tests/unit/device_plugins/extr_haake/test_plugin.py tests/unit/device_plugins/mix_eirich/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor_branches.py tests/unit/device_plugins/test_device/test_test_device_file_processor.py tests/unit/device_plugins/utm_zwick/test_file_processor.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `754 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `754 passed, 1 skipped, 1 warning`, `TOTAL 5446 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 17 `LocalRecord` Empty-Separator Fallback Removal (2026-03-02)
- Intended actions:
  - remove residual `LocalRecord` post-init fallback that coerced empty
    separators to `"-"`.
- Observed outcome:
  - `LocalRecord.__post_init__` now requires non-empty `id_separator` context
    and fails fast when missing;
  - added focused unit coverage for empty-separator construction failure.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py::test_init_rejects_empty_separator_value` -> failed (did not raise `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py tests/unit/application/records/test_record_manager.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/storage/test_filesystem_utils.py` -> `90 passed, 1 skipped`
    - `python -m ruff check src/dpost/domain/records/local_record.py tests/unit/domain/records/test_local_record.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `755 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `755 passed, 1 skipped, 1 warning`, `TOTAL 5447 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 18 UTM Flush Runtime-Context Contract Tightening (2026-03-02)
- Intended actions:
  - remove silent skip behavior when UTM deferred flush runs without explicit
    runtime context.
- Observed outcome:
  - UTM `flush_incomplete()` now requires explicit runtime `id_separator` and
    `dest_dir` context during staged flush execution;
  - missing-context flush calls now fail fast instead of logging/continuing;
  - added focused branch tests for missing-context error and configured flush
    success.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py -k "flush_incomplete_requires_explicit_separator_context or flush_incomplete_processes_staged_series_with_runtime_context"` -> failed (flush silently skipped missing-context series)
  - green-state:
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py -k "flush_incomplete_requires_explicit_separator_context or flush_incomplete_processes_staged_series_with_runtime_context"` -> `2 passed, 6 deselected`
    - `python -m pytest -q tests/unit/device_plugins/utm_zwick` -> `17 passed`
    - `python -m pytest -q tests/unit` -> `758 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `758 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 19 Package-Level Config Context Export Narrowing (2026-03-02)
- Intended actions:
  - reduce ambient helper surface by removing package-level config re-exports
    for `current/get_service/set_service`.
- Observed outcome:
  - `dpost.application.config` no longer re-exports ambient context helpers;
  - tests requiring ambient helpers now import from
    `dpost.application.config.context` explicitly;
  - added unit guard ensuring ambient helpers remain out of package namespace.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py::test_config_package_namespace_omits_ambient_service_helpers` -> failed (`current` still exported from package)
  - green-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py tests/integration/test_settings_integration.py` -> `6 passed`
    - `python -m pytest -q tests/unit/device_plugins/extr_haake/test_plugin.py` -> `5 passed`
    - `python -m pytest -q tests/unit` -> `759 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `759 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 20 Config Lifecycle Helper Re-Export Removal (2026-03-02)
- Intended actions:
  - remove package-level config re-exports for `init_config`,
    `reset_service`, and `activate_device`.
- Observed outcome:
  - `dpost.application.config` no longer re-exports lifecycle/context helper
    symbols;
  - runtime-adapter and test call sites now import lifecycle helpers from
    `dpost.application.config.context` explicitly;
  - added namespace guard coverage for lifecycle helper export boundaries.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py::test_config_package_namespace_omits_context_lifecycle_helpers` -> failed (`init_config` still exported from package)
  - green-state:
    - `python -m pytest -q tests/unit/application/config/test_context.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py tests/integration/test_settings_integration.py` -> `29 passed`
    - `python -m pytest -q tests/unit/infrastructure/runtime/test_startup_dependencies.py` -> `6 passed`
    - `python -m pytest -q tests/unit` -> `760 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `760 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 21 Explicit LocalRecord Constructor Separator Context (2026-03-02)
- Intended actions:
  - finish interrupted `LocalRecord` strict-separator constructor cleanup.
- Observed outcome:
  - `LocalRecord.id_separator` typing is now normalized to `str` with
    fail-fast missing/empty validation still enforced in `__post_init__`;
  - direct unit-test `LocalRecord(...)` constructor call sites now pass
    explicit separator context (`id_separator="-"`) where required;
  - focused missing-separator constructor coverage remains in
    `tests/unit/domain/records/test_local_record.py`.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py` -> failed (test fixtures/callers omitted explicit separator context)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_processor_abstract.py tests/unit/application/processing/test_record_utils.py tests/unit/application/processing/test_route_context_policy.py tests/unit/application/session/test_session_manager.py tests/unit/application/records/test_record_manager.py tests/unit/domain/processing/test_routing.py tests/unit/domain/records/test_local_record.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/erm_hioki/test_file_processor_branches.py tests/unit/device_plugins/extr_haake/test_plugin.py tests/unit/device_plugins/mix_eirich/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/test_device/test_test_device_file_processor.py` -> `232 passed, 1 skipped`
    - `python -m pytest -q tests/unit` -> `760 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `760 passed, 1 skipped, 1 warning`, `TOTAL 5450 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 22 LocalRecord Signature-Level Strictness (2026-03-02)
- Intended actions:
  - enforce explicit separator requirements at `LocalRecord` signature level.
- Observed outcome:
  - `LocalRecord.id_separator` is now a required keyword-only constructor
    argument;
  - `LocalRecord.from_dict(...)` now requires explicit `id_separator` in the
    method signature;
  - focused hydration coverage now includes empty-string separator rejection.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py -k "test_init_rejects_missing_separator_value or test_from_dict_requires_explicit_separator"` -> `2 failed` (runtime-validation exception type mismatch)
  - green-state:
    - `python -m pytest -q tests/unit/domain/records/test_local_record.py` -> `23 passed`
    - `python -m pytest -q tests/unit` -> `761 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `761 passed, 1 skipped, 1 warning`, `TOTAL 5451 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 23 FileProcessManager Pipeline Module Extraction (2026-03-02)
- Intended actions:
  - decompose the embedded processing pipeline implementation from
    `FileProcessManager`.
- Observed outcome:
  - moved `_ProcessingPipeline` from
    `application/processing/file_process_manager.py` to
    `application/processing/processing_pipeline.py`;
  - kept manager runtime wiring stable (`self._pipeline`) and updated
    pipeline-related monkeypatch path coverage in branch tests;
  - reduced `file_process_manager.py` orchestration footprint while preserving
    behavior.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k test_init_uses_dedicated_processing_pipeline_type` -> failed (`ModuleNotFoundError`)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k "test_init_uses_dedicated_processing_pipeline_type or test_non_accept_route_stage_uses_record_flow_for_unappendable or test_process_item_defers_when_resolution_requests_retry"` -> `3 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_force_paths_kadi_sync.py` -> `49 passed`
    - `python -m ruff check src/dpost/application/processing/file_process_manager.py src/dpost/application/processing/processing_pipeline.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `All checks passed!`

## Progress Update: Section 24 Record Persistence Context Helper Extraction (2026-03-02)
- Intended actions:
  - extract record-persistence context assembly from manager stage code.
- Observed outcome:
  - added
    `application/processing/record_persistence_context.py` with
    `RecordPersistenceContext` and
    `build_record_persistence_context(...)`;
  - updated
    `FileProcessManager._resolve_record_persistence_context_stage(...)` to
    delegate to the helper while preserving explicit
    separator/path/device context forwarding;
  - added focused helper unit coverage.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_record_persistence_context.py` -> failed (`ModuleNotFoundError`)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_record_persistence_context.py` -> `2 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py` -> `49 passed`
    - `python -m ruff check src/dpost/application/processing/file_process_manager.py src/dpost/application/processing/processing_pipeline.py src/dpost/application/processing/record_persistence_context.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_record_persistence_context.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `764 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `764 passed, 1 skipped, 1 warning`, `TOTAL 5481 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 25 Naming Policy Signature-Level Explicit-Context Contracts (2026-03-02)
- Intended actions:
  - enforce explicit separator/pattern requirements at naming facade function
    signatures.
- Observed outcome:
  - tightened `application/naming/policy.py` signatures so explicit
    `id_separator` / `filename_pattern` context is required where applicable;
  - updated naming facade tests to assert missing-context `TypeError` behavior;
  - retained defensive runtime guard coverage for empty-separator and explicit
    `None` pattern values.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/naming/test_policy.py` -> `4 failed` (old optional signatures still raised `ValueError`)
  - green-state:
    - `python -m pytest -q tests/unit/application/naming/test_policy.py` -> `11 passed`
    - `python -m pytest -q tests/unit/application/processing/test_routing_helpers.py tests/unit/application/processing/test_rename_flow.py tests/unit/application/records/test_record_manager.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py` -> `38 passed, 1 skipped`
    - `python -m pytest -q tests/unit` -> `766 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `766 passed, 1 skipped, 1 warning`, `TOTAL 5481 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 26 Processing Pipeline Runtime Adapter Decoupling (2026-03-02)
- Intended actions:
  - add a dedicated runtime adapter seam so the extracted processing pipeline no
    longer reaches manager internals directly.
- Observed outcome:
  - added
    `application/processing/processing_pipeline_runtime.py` with
    `ProcessingPipelineRuntime` as the manager-collaborator adapter;
  - updated
    `application/processing/processing_pipeline.py` to consume the runtime
    adapter seam;
  - updated
    `FileProcessManager` wiring to create and inject
    `self._pipeline_runtime`;
  - added branch coverage asserting adapter wiring during manager
    initialization.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k test_init_uses_processing_pipeline_runtime_adapter` -> failed (`ModuleNotFoundError: dpost.application.processing.processing_pipeline_runtime`)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py` -> `33 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/application/processing/test_record_persistence_context.py tests/unit/application/naming/test_policy.py` -> `30 passed`
    - `python -m pytest -q tests/unit` -> `767 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `767 passed, 1 skipped, 1 warning`, `TOTAL 5524 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 27 Processor Runtime-Context Helper Extraction (2026-03-02)
- Intended actions:
  - extract processor runtime-context mapping from
    `FileProcessManager._resolve_processor(...)` into a dedicated helper seam.
- Observed outcome:
  - added
    `application/processing/processor_runtime_context.py` with
    `ProcessorRuntimeContext`,
    `build_processor_runtime_context(...)`, and
    `apply_processor_runtime_context(...)`;
  - updated manager processor resolution stage to delegate explicit runtime
    context build/apply behavior to the helper seam;
  - added focused helper coverage validating config-derived context payload and
    processor context injection.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_processor_runtime_context.py` -> failed (`ModuleNotFoundError: dpost.application.processing.processor_runtime_context`)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_processor_runtime_context.py tests/unit/application/processing/test_file_process_manager_branches.py -k "processor_runtime_context or resolve_processor_injects_runtime_context_into_processor or resolve_processor_uses_factory_when_instance_processor_missing"` -> `4 passed, 31 deselected`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_processor_runtime_context.py tests/unit/application/processing/test_force_paths_kadi_sync.py` -> `52 passed`
    - `python -m ruff check src/dpost/application/processing/file_process_manager.py src/dpost/application/processing/processor_runtime_context.py tests/unit/application/processing/test_processor_runtime_context.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `769 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `769 passed, 1 skipped, 1 warning`, `TOTAL 5541 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 28 Processing Pipeline Runtime Protocol Contract (2026-03-02)
- Intended actions:
  - introduce an explicit protocol contract for pipeline/runtime interactions so
    `_ProcessingPipeline` no longer depends on a concrete adapter type.
- Observed outcome:
  - added runtime-checkable
    `ProcessingPipelineRuntimePort` in
    `application/processing/processing_pipeline_runtime.py`;
  - tightened adapter typing annotations so `ProcessingPipelineRuntime` conforms
    to the protocol seam;
  - updated `_ProcessingPipeline` constructor typing to accept
    `ProcessingPipelineRuntimePort`;
  - added branch coverage assertion that manager runtime adapter satisfies the
    protocol.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k test_init_uses_processing_pipeline_runtime_adapter` -> failed (`ImportError: cannot import name 'ProcessingPipelineRuntimePort'`)
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py -k test_init_uses_processing_pipeline_runtime_adapter` -> `1 passed, 32 deselected`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/application/processing/test_processor_runtime_context.py` -> `52 passed`
    - `python -m ruff check src/dpost/application/processing/processing_pipeline.py src/dpost/application/processing/processing_pipeline_runtime.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `769 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `769 passed, 1 skipped, 1 warning`, `TOTAL 5544 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 29 Processing Orchestration Wrapper-Sprawl Consolidation (2026-03-03)
- Intended actions:
  - reduce low-value stage-wrapper indirection in processing orchestration while
    preserving behavior and the meaningful seams (`failure_outcome_policy`,
    failure emitter, runtime adapter contract).
- Observed outcome:
  - in `file_process_manager.py`, inlined wrapper-only
    `add_item_to_record(...)` processing/finalization stages and removed:
    `_process_record_artifact_stage(...)`,
    `_assign_record_datatype_stage(...)`, and
    `_finalize_record_output_stage(...)`;
  - inlined immediate-sync error emitter invocation and failure-outcome
    construction within existing stage methods (removed
    `_emit_immediate_sync_error_stage(...)` and
    `_build_processing_failure_outcome_stage(...)`);
  - in `processing_pipeline.py`, removed wrapper-only `_preprocess_stage(...)`
    and `_build_route_context(...)` indirection layers, keeping
    `_route_decision_stage(...)` as the single routing-context seam.
- Validation:
  - green-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/application/processing/test_processor_runtime_context.py` -> `52 passed`
    - `python -m ruff check src/dpost/application/processing/file_process_manager.py src/dpost/application/processing/processing_pipeline.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `769 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `769 passed, 1 skipped, 1 warning`, `TOTAL 5530 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Progress Update: Section 30 Sprawl Stop-Line and Boundary Clarification (2026-03-03)
- Intended actions:
  - finish the post-consolidation posture by accepting an explicit stop-line
    and reducing remaining low-value facade/adapter boilerplate.
- Observed outcome:
  - finalized sprawl posture RPC status and stop-line criteria in
    `docs/planning/archive/20260303-processing-sprawl-posture-rpc.md`;
  - simplified application naming facade implementation shape in
    `application/naming/policy.py` by reducing alias-heavy imports and
    consolidating repeated explicit naming-context validation;
  - simplified `processing_pipeline_runtime.py` local implementation by caching
    stable collaborators + centralizing active-config lookup while preserving
    dynamic seam behavior used by branch tests.
- Validation:
  - red-state:
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/application/processing/test_processor_runtime_context.py` -> `7 failed, 45 passed` (callable caching altered dynamic seam behavior)
  - green-state:
    - `python -m pytest -q tests/unit/application/naming/test_policy.py` -> `11 passed`
    - `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/application/processing/test_processor_runtime_context.py` -> `52 passed`
    - `python -m ruff check src/dpost/application/processing/processing_pipeline_runtime.py src/dpost/application/naming/policy.py` -> `All checks passed!`
    - `python -m pytest -q tests/unit` -> `769 passed, 1 skipped, 1 warning`
    - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `769 passed, 1 skipped, 1 warning`, `TOTAL 5526 stmts, 0 miss, 100%`
    - `python -m ruff check .` -> `All checks passed!`
    - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Final Status for This Wave
- Sections 1-5 of the migration checklist are complete.
- Sections 6 and 13 runtime naming-overload rename slices are complete.
- Section 8 record/persistence separator-inference cleanup is complete.
- Naming policy ownership remains centralized in `NamingSettings`, and the
  runtime orchestration hot paths now require explicit naming context.
- Section 12 storage unique-name separator fallback cleanup is complete.
- Section 14 post-checklist explicit-context cleanup is complete.
- Section 15 plugin exception-dir parent fallback cleanup is complete.
- Section 16 remaining plugin separator fallback cleanup is complete.
- Section 17 LocalRecord empty-separator fallback cleanup is complete.
- Section 18 UTM flush runtime-context contract cleanup is complete.
- Section 19 package-level config context export narrowing is complete.
- Section 20 config lifecycle helper re-export cleanup is complete.
- Section 21 explicit `LocalRecord` constructor separator cleanup is complete.
- Section 22 `LocalRecord` signature-level strictness cleanup is complete.
- Section 23 `FileProcessManager` pipeline module extraction is complete.
- Section 24 record-persistence context helper extraction is complete.
- Section 25 naming-policy signature-level explicit-context cleanup is complete.
- Section 26 processing-pipeline runtime adapter decoupling is complete.
- Section 27 processor runtime-context helper extraction is complete.
- Section 28 processing-pipeline runtime protocol contract is complete.
- Section 29 processing orchestration wrapper-sprawl consolidation is complete.
- Section 30 sprawl stop-line and boundary clarification follow-through is complete.
- No deferred compatibility fallback seams remain in active migration scope.

