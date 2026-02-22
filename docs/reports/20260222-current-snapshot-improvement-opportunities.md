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
