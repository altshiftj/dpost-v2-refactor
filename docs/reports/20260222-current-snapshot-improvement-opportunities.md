# Current Snapshot Improvement Opportunities (2026-02-22)

## Summary

This report captures the most actionable improvement opportunities observed from
the current green test snapshot (`706 passed, 1 skipped`) after recent
coverage-driven refactors and integration regression fixes.

The emphasis is on design risk reduction and operational determinism rather than
coverage expansion.

## Prioritized Opportunities

## 1. Device Resolver / Pipeline Resolution Semantics (Highest ROI)

Why this matters:
- `DeviceResolution` currently mixes `selected`, `deferred`, and `retry_delay`
  fields, which allows ambiguous combinations and pushes interpretation logic
  into callers.
- The processing pipeline has already needed defensive fixes for race windows
  where path disappearance semantics were not explicit.

Primary evidence:
- `src/dpost/application/processing/device_resolver.py`
- `src/dpost/application/processing/file_process_manager.py`

Recommendation:
- Introduce an explicit resolution kind/outcome model (`accept`, `defer`,
  `reject`) with typed constructors/helpers.
- Update `FileProcessManager` to branch on explicit outcome semantics instead of
  implicit field combinations.
- Keep compatibility properties during migration where practical.

Expected outcome:
- Fewer state-interpretation bugs (especially around missing/disappearing paths).
- Clearer tests and easier future resolver changes.

## 2. Stability vs Resolver Deferral Responsibility Clarification

Why this matters:
- Disappear/reappear behavior is split across resolver and stability stages.
- Recent regressions showed that stubs/optimistic behavior in one stage can let
  invalid states leak into later stages.

Primary evidence:
- `src/dpost/application/processing/stability_tracker.py`
- `src/dpost/application/processing/file_process_manager.py`

Recommendation:
- Move toward a tri-state stability outcome (`stable`, `defer`, `reject`) so
  retry/deferral semantics stay centralized.

## 3. Logging Setup Is Process-Global and Test-Hostile

Why this matters:
- Logging initializes `C:/Watchdog/logs` and rotating file handlers for many
  test runs, producing noisy `RotatingFileHandler` permission errors and cross-
  process contention.

Primary evidence:
- `src/dpost/infrastructure/logging.py`

Recommendation:
- Make file logging opt-in/configurable (environment or runtime config).
- Prefer console/null handlers by default in tests and headless fixtures.

## 4. Plugin Loader Lazy-Load Reentrancy / Mutability Hardening

Why this matters:
- `PluginLoader` mutates plugin manager state and registries during lazy load
  without synchronization.
- Event-heavy integrations and nested lazy-loading can stress duplicate
  registration paths.

Primary evidence:
- `src/dpost/plugins/system.py`

Recommendation:
- Add a re-entrant lock (`threading.RLock`) around lazy-load / refresh /
  registration paths.
- Consider explicit refresh-state guards to prevent re-entrant registry rebuilds.

## 5. Post-Persist Side Effects Are Still a Heavy Cluster

Why this matters:
- Record updates, force-path bookkeeping, metrics, immediate sync, logging, and
  UI error surfacing are still coupled in one method.

Primary evidence:
- `src/dpost/application/processing/file_process_manager.py` (`_post_persist_side_effects_stage`)

Recommendation:
- Extract an immediate-sync error emission sink (similar to
  `failure_emitter.py`), then continue decomposing post-persist side effects.

## 6. Constructor Side Effects in FileProcessManager

Why this matters:
- `FileProcessManager.__init__` may trigger startup sync immediately, which
  increases constructor cost and makes test/setup behavior less explicit.

Primary evidence:
- `src/dpost/application/processing/file_process_manager.py`

Recommendation:
- Move startup sync into an explicit startup method or composition-root step.

## 7. Integration Fixtures Should Prefer Explicit Observer Injection

Why this matters:
- Integration tests currently mix pre-construction and post-construction
  monkeypatch strategies for observer creation, which is easy to get wrong.

Primary evidence:
- `tests/integration/test_device_integrations.py`
- `tests/integration/test_multi_processor_app_flow.py`
- `tests/integration/test_extr_haake_safesave.py`

Recommendation:
- Pass `observer_factory=` directly to `DeviceWatchdogApp` in fixtures.
- Reduce module-level monkeypatching for runtime dependencies when constructor
  seams exist.

## 8. Test Scheduler Lacks Time Semantics

Why this matters:
- `HeadlessUI` schedules callbacks without honoring delay, and
  `drain_scheduled_tasks()` executes immediately.
- This can hide timing behavior and create subtle expectations in retry tests.

Primary evidence:
- `tests/helpers/fake_ui.py`
- `tests/helpers/task_runner.py`

Recommendation:
- Add a lightweight virtual-time scheduler fake for integration tests that care
  about retry timing or safe-save reappearance behavior.

## Recommended Next Execution Order

1. Device resolver explicit outcome semantics (this slice)
2. Logging configurability / test-safe defaults
3. Plugin loader lock/reentrancy hardening
4. File-process manager post-persist sync-error boundary extraction

## Progress Update: Device Resolver Explicit Outcome Semantics (Completed Slice)

Intended action:
- Make resolver outcomes explicit so pipeline callers do not rely on implicit
  combinations of `selected` + `deferred` booleans.

Observed outcome:
- Added `DeviceResolutionKind` and explicit constructors on `DeviceResolution`
  (`accept`, `defer`, `reject`) in
  `src/dpost/application/processing/device_resolver.py`.
- Updated resolver return paths to construct explicit outcomes.
- Updated `FileProcessManager` to branch on `resolution.kind` instead of only
  `resolution.deferred` in
  `src/dpost/application/processing/file_process_manager.py`.
- Expanded unit tests to assert `kind` semantics and validate invalid ACCEPT
  construction.

Validation:
- `python -m ruff check src/dpost/application/processing/device_resolver.py src/dpost/application/processing/file_process_manager.py tests/unit/application/processing/test_device_resolver.py tests/unit/application/processing/test_file_process_manager_branches.py` -> pass
- `python -m pytest -q tests/unit/application/processing/test_device_resolver.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `46 passed`
- `python -m pytest -q` -> `707 passed, 1 skipped, 1 warning`

## Progress Update: Stability vs Resolver Deferral Boundary (In Progress / Incremental Slice)

Intended action:
- Introduce explicit stability-stage outcome semantics (`stable`, `defer`,
  `reject`) without changing safe-save behavior that currently depends on
  blocking reappear handling inside `FileStabilityTracker.wait()`.

Observed outcome:
- Added `StabilityOutcomeKind` and explicit `StabilityOutcome` constructors
  (`stable_result`, `defer`, `reject`) in
  `src/dpost/application/processing/stability_tracker.py`.
- Preserved backward compatibility for existing call sites/tests by inferring
  `kind` from legacy `stable=True/False` construction in `__post_init__`.
- Updated `_stabilize_artifact_stage()` in
  `src/dpost/application/processing/file_process_manager.py` to honor explicit
  deferred stability outcomes and return `ProcessingStatus.DEFERRED` with retry
  delay when provided.
- Expanded unit tests to assert explicit stability outcome semantics and manager
  deferral handling.

Expected next outcome (later slice):
- Consider returning `StabilityOutcome.defer(...)` directly from
  `FileStabilityTracker.wait()` for selected retry cases, after validating that
  EXTR safe-save integration behavior remains unchanged.

## Progress Update: Logging Setup Test-Hostility Reduction (Completed Slice)

Intended action:
- Remove import-time filesystem side effects from logging setup and make file
  logging opt-in/overridable in tests without broad monkeypatching.

Observed outcome:
- `src/dpost/infrastructure/logging.py` no longer creates `C:/Watchdog/logs`
  at import time.
- File-handler setup is now lazy inside `setup_logger(...)`, guarded by a
  policy helper and wrapped so file-access failures do not break startup.
- Added env-driven control:
  - `DPOST_LOG_FILE_ENABLED` (`true/false`, etc.)
  - `DPOST_LOG_FILE_PATH` (with fallback to existing `LOG_FILE_PATH`)
- Pytest runs now default to console/null logging unless file logging is
  explicitly re-enabled, which reduces shared-path contention and permission
  noise during tests.
- Expanded unit tests in `tests/unit/infrastructure/test_logging.py` to cover:
  pytest-default file logging disablement, explicit enablement, and file-handler
  failure fallback.

Validation:
- `python -m pytest -q tests/unit/infrastructure/test_logging.py` -> `5 passed`
- `python -m pytest -q` -> `715 passed, 1 skipped, 1 warning`
- `python -m ruff check .` -> pass

## Progress Update: Plugin Loader Reentrancy / Mutability Hardening (Completed Slice)

Intended action:
- Reduce race windows and reentrancy hazards in `PluginLoader` lazy-loading and
  registry refresh flows without changing plugin discovery semantics.

Observed outcome:
- Added an internal `threading.RLock` to `PluginLoader` and wrapped mutable
  operations, including:
  - refresh methods (`refresh`, `refresh_devices`, `refresh_pcs`)
  - lazy-load/discovery paths (`_load_entrypoints`, `_load_builtin_plugins`,
    `_lazy_load_builtin`, `_lazy_load_entrypoint`)
  - plugin registration (`register_plugin`, `_register_module`)
  - plugin-availability reads (`available_device_plugins`,
    `available_pc_plugins`) for consistent snapshots during refreshes
- Hardened singleton initialization in `get_plugin_loader()` with a module-level
  lock (double-checked locking pattern) to avoid duplicate loader construction
  under concurrent access.
- Added unit tests covering:
  - nested/reentrant lock acquisition during loader discovery operations
  - singleton initialization serialization under a thread race

Validation:
- `python -m pytest -q tests/unit/plugins/system/test_plugin_loader.py tests/unit/plugins/system/test_plugin_loader_discovery_edges.py tests/unit/plugins/system/test_plugin_loader_residual_branches.py tests/unit/plugins/system/test_no_double_logging.py` -> `26 passed`
- `python -m pytest -q` -> `717 passed, 1 skipped, 1 warning`
- `python -m ruff check .` -> pass

## Progress Update: Post-Persist Sync-Error Boundary Extraction (Completed Slice)

Intended action:
- Reduce coupling inside `_post_persist_side_effects_stage()` by extracting the
  immediate-sync error reporting path (log + UI error) behind an injectable
  seam.

Observed outcome:
- Added `src/dpost/application/processing/immediate_sync_error_emitter.py` with:
  - `ImmediateSyncErrorEmissionSink`
  - `emit_immediate_sync_error(...)`
- Wired `FileProcessManager` to use an injected/default immediate-sync error
  sink and moved immediate-sync error side effects into
  `_emit_immediate_sync_error_stage(...)`.
- Preserved existing post-persist behavior and branch tests while adding a
  dedicated seam-level unit test.

Validation:
- Targeted unit tests + branch coverage checks passed
- Included in final full checkpoint (`726 passed, 1 skipped, 1 warning`)

## Progress Update: FileProcessManager Constructor Side-Effect Reduction (Completed Slice)

Intended action:
- Remove startup record-sync work from `FileProcessManager.__init__` and make it
  an explicit composition-root lifecycle step.

Observed outcome:
- `FileProcessManager.__init__` no longer triggers startup sync.
- Added explicit one-time hook:
  - `FileProcessManager.run_startup_sync_if_pending()`
- Wired `DeviceWatchdogApp.initialize()` to invoke the hook, preserving runtime
  startup behavior while keeping constructor setup deterministic.
- Added tests proving:
  - constructor is side-effect free
  - startup sync hook is idempotent
  - app initialization invokes the explicit hook

Validation:
- Targeted runtime/processing unit tests passed
- Included in final full checkpoint (`726 passed, 1 skipped, 1 warning`)

## Progress Update: Integration Observer Injection Cleanup (Completed Slice)

Intended action:
- Replace integration-time module monkeypatching of `Observer` with explicit
  `observer_factory=` injection to match the existing `DeviceWatchdogApp` seam.

Observed outcome:
- Updated integration fixtures in:
  - `tests/integration/test_device_integrations.py`
  - `tests/integration/test_integration.py`
  - `tests/integration/test_extr_haake_safesave.py`
  - `tests/integration/test_multi_processor_app_flow.py`
- Fixtures now pass `observer_factory=lambda: FakeObserver()` directly, reducing
  global monkeypatch timing risks and fixture coupling to module globals.

Validation:
- Targeted integration subset passed
- Included in final full checkpoint (`726 passed, 1 skipped, 1 warning`)

## Progress Update: Virtual-Time Test Scheduler Helper (Completed Slice)

Intended action:
- Add a lightweight scheduler fake mode that honors delays for tests that need
  retry timing semantics, without breaking existing immediate-drain test flows.

Observed outcome:
- Added opt-in virtual-time support to `tests/helpers/fake_ui.py`:
  - `HeadlessUI(use_virtual_time=True)`
  - virtual time tracking + due-task execution helpers
- Extended `tests/helpers/task_runner.py` with:
  - virtual-aware `drain_scheduled_tasks(...)`
  - `advance_scheduled_time(...)`
- Added unit tests for virtual scheduler behavior:
  - `tests/unit/test_task_runner_virtual_time.py`
- Added a delay-aware integration test in `tests/integration/test_integration.py`
  that explicitly advances virtual time to validate retry enqueue timing.

Validation:
- Targeted helper + integration subset passed (`72 passed`)
- `python -m pytest -q` -> `726 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `691 passed, 1 skipped, 1 warning`, `100%` total coverage
- `python -m ruff check .` -> pass

## Checklist Status (2026-02-22 Final)

All eight prioritized improvement opportunities in this report have now been
addressed as completed slices or intentional incremental refactor steps
(notably item 2, which is complete for explicit outcome semantics and leaves a
documented optional follow-up to emit deferred outcomes directly from the
stability tracker).

## Continuation Slice: Post-Persist Bookkeeping Plan/Emitter Extraction (2026-02-22)

Intended action:
- Continue item 5 decomposition by separating force-path bookkeeping planning
  (update targets + unsynced marks + skipped missing paths) from side-effect
  emission in `FileProcessManager`.

Observed outcome:
- Added `src/dpost/application/processing/post_persist_bookkeeping.py` with:
  - `PostPersistBookkeepingPlan`
  - `PostPersistRecordUpdateTarget`
  - `PostPersistBookkeepingEmissionSink`
  - `build_post_persist_bookkeeping_plan(...)`
  - `emit_post_persist_bookkeeping(...)`
- Updated `FileProcessManager` to:
  - build a bookkeeping plan
  - log skipped missing force paths in a dedicated stage
  - emit bookkeeping side effects through a dedicated stage/sink builder
- Preserved existing branch behavior for force-file/force-dir handling and
  immediate-sync error reporting.
- Added focused seam tests in
  `tests/unit/application/processing/test_post_persist_bookkeeping.py`.

Validation:
- `python -m pytest -q` -> `729 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `694 passed, 1 skipped, 1 warning`, `100%` total coverage (`5312 stmts, 0 miss`)
- `python -m ruff check .` -> pass

## Continuation Slice: RecordManager Explicit Persistence Context Wiring (2026-02-22)

Intended action:
- Reduce hidden global config access in core record orchestration by making
  persisted-record path and record id-separator explicit in `RecordManager`.

Observed outcome:
- `src/dpost/application/records/record_manager.py` now accepts:
  - `persisted_records_path`
  - `id_separator`
- Lazy load / reload / save paths now forward explicit values to
  `load_persisted_records(...)` / `save_persisted_records(...)` instead of
  relying on `filesystem_utils` global runtime config defaults.
- `FileProcessManager` now passes config-derived values when constructing
  `RecordManager`, reducing hidden runtime coupling in the processing path.
- Added focused unit tests verifying explicit-path/separator forwarding.

Validation:
- `python -m pytest -q` -> `732 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `697 passed, 1 skipped, 1 warning`, `100%` total coverage (`5316 stmts, 0 miss`)
- `python -m ruff check .` -> pass

## Continuation Slice: Processing Routing Explicit Naming Context (2026-02-22)

Intended action:
- Remove hidden naming-policy runtime context reads from the processing routing
  hot path by passing explicit naming context through `fetch_record_for_prefix`.

Observed outcome:
- `src/dpost/application/processing/routing.py`
  - `fetch_record_for_prefix(...)` now accepts optional explicit
    `filename_pattern` and `id_separator`
  - forwards explicit naming context to `sanitize_and_validate(...)`
  - forwards explicit separator + current device to `generate_record_id(...)`
- `src/dpost/application/processing/file_process_manager.py`
  - `_build_route_context(...)` now passes `manager.config_service.current`
    naming values into `fetch_record_for_prefix(...)`
- `tests/unit/application/processing/test_routing_helpers.py`
  - updated to assert explicit kwarg forwarding behavior

Validation:
- `python -m pytest -q` -> `732 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `697 passed, 1 skipped, 1 warning`, `100%` total coverage (`5317 stmts, 0 miss`)
- `python -m ruff check .` -> pass

## Continuation Slice: FileProcessManager Persistence Context Explicit Forwarding (2026-02-22)

Intended action:
- Remove hidden naming/storage context reads from the record-persistence hot
  path by explicitly forwarding config-derived context into naming/storage
  helpers in `FileProcessManager`.

Observed outcome:
- `src/dpost/application/processing/file_process_manager.py`
  - `_resolve_record_persistence_context_stage(...)` now forwards explicit:
    - `id_separator`
    - `dest_dir`
    - `current_device`
    into `get_record_path(...)`
  - also forwards explicit `id_separator` and `current_device` into
    `generate_file_id(...)`
- Added focused branch test in
  `tests/unit/application/processing/test_file_process_manager_branches.py`
  asserting explicit kwarg forwarding to both helpers.

Validation:
- `python -m pytest -q` -> `733 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `698 passed, 1 skipped, 1 warning`, `100%` total coverage (`5318 stmts, 0 miss`)
- `python -m ruff check .` -> pass

## Continuation Slice: Exception-Path Context Explicit Forwarding (2026-02-22)

Intended action:
- Reduce hidden global storage-context reads in reject/failure flows by passing
  explicit exception-folder context (`exception_dir`, `id_separator`) through
  processing error-handling and storage helpers.

Observed outcome:
- `src/dpost/application/processing/error_handling.py`
  - `safe_move_to_exception(...)` now accepts optional explicit
    `exception_dir` and `id_separator` and forwards them to
    `move_to_exception_folder(...)`.
- `src/dpost/application/processing/file_process_manager.py`
  - added context-aware exception-move helpers for reject/failure stages
  - reject, no-processor, and failure-emission paths now use explicit
    config-derived exception context instead of relying on storage helper
    runtime-config defaults
- `src/dpost/infrastructure/storage/filesystem_utils.py`
  - `move_to_exception_folder(...)` now accepts optional explicit `base_dir`
    and `id_separator`, forwarding them to `get_exception_path(...)`
- Tests expanded to cover:
  - explicit exception-context forwarding in processing error handling
  - manager helper forwarding into storage move helpers
  - explicit exception context support in `move_to_exception_folder(...)`
  - default `_exceptions_dir()` wrapper path coverage (compatibility wrapper)

Validation:
- `python -m pytest -q` -> `738 passed, 1 skipped, 1 warning`
- `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `703 passed, 1 skipped, 1 warning`, `100%` total coverage (`5324 stmts, 0 miss`)
- `python -m ruff check .` -> pass
