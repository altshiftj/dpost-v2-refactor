# Full Legacy Repo Retirement Inventory

## Date
- 2026-02-21

## Goal
- Establish a concrete baseline for retiring the remaining legacy repository
  surface under `src/ipat_watchdog/**` while preserving functional parity.

## Baseline Snapshot
- Legacy source files:
  - `src/ipat_watchdog/**` files: `615`
  - `src/ipat_watchdog/**/*.py` files: `119`
  - `src/ipat_watchdog/core/**/*.py`: `46`
  - `src/ipat_watchdog/device_plugins/**/*.py`: `42`
  - `src/ipat_watchdog/pc_plugins/**/*.py`: `26`
- Legacy references:
  - `ipat_watchdog` references in `src/**`: `307`
  - `ipat_watchdog` references in `tests/**`: `307`
  - `ipat_watchdog` references in `docs/**`: `277`
- Test estate:
  - `tests/unit/**/*.py`: `61`
  - `tests/integration/**/*.py`: `8`
  - `tests/manual/**/*.py`: `2`

## Existing Documentation Coverage
- Strong coverage exists for canonical runtime decoupling through Phase 9-13:
  - `docs/planning/20260221-dpost-full-legacy-decoupling-clean-architecture-roadmap.md`
  - `docs/checklists/20260221-dpost-full-legacy-decoupling-clean-architecture-checklist.md`
  - `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`
- Existing docs do not yet provide a full, end-to-end retirement execution plan
  for deleting the legacy package tree and migrating legacy test ownership.

## Gap Assessment
- Missing explicit end-state criteria for:
  - retiring `src/ipat_watchdog/core/**`
  - retiring `src/ipat_watchdog/device_plugins/**`
  - retiring `src/ipat_watchdog/pc_plugins/**`
  - retiring legacy-targeted test imports and fixtures.
- Missing phased plan that coordinates:
  - source retirement
  - test migration
  - packaging/entrypoint cleanup
  - contributor docs and release communication.

## Retirement Target State
- Canonical runtime, plugins, and extension contracts live under `src/dpost/**`.
- No runtime or test-critical dependency on `src/ipat_watchdog/**`.
- Legacy package tree is removed (or reduced to intentionally scoped stubs with
  explicit retirement date, if required temporarily).
- Architecture/testing docs and contributor docs describe only canonical dpost
  flows.

## Companion Artifacts
- Roadmap:
  - `docs/planning/20260221-full-legacy-repo-retirement-roadmap.md`
- Checklist:
  - `docs/checklists/20260221-full-legacy-repo-retirement-checklist.md`

## Progress Update (Kickoff Increment)
- Added migration guard test coverage for shared harness retirement:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py`
- Removed legacy imports from shared helper boundaries:
  - `tests/helpers/fake_ui.py`
  - `tests/helpers/fake_sync.py`
  - `tests/helpers/fake_process_manager.py`
  - `tests/helpers/fake_processor.py`
- Removed hardcoded legacy module literal from conftest observer patch:
  - `tests/conftest.py` now resolves observer patch target from
    `DeviceWatchdogApp.__module__`.
- Migrated shared watchdog fixture runtime import to canonical dpost runtime:
  - `tests/conftest.py`
  - `tests/unit/core/app/test_device_watchdog_app.py`
- Migrated integration runtime app imports/observer targets to canonical dpost
  runtime ownership:
  - `tests/integration/test_integration.py`
  - `tests/integration/test_multi_processor_app_flow.py`
  - `tests/integration/test_device_integrations.py`
  - `tests/integration/test_extr_haake_safesave.py`
- Retired direct Prometheus collector definitions from legacy metrics module:
  - `src/ipat_watchdog/metrics.py` now re-exports canonical
    `dpost.application.metrics` symbols.
- Verification snapshots:
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py`
    -> `2 failed` (red), then `2 passed` (green), then
    `1 failed, 2 passed` (red after added process-manager guard), then
    `3 passed` (green), then `1 failed, 3 passed` (red after conftest guard),
    then `4 passed` (green), then `1 failed, 4 passed` (red after
    fake-processor guard), then `5 passed` (green), then
    `1 failed, 5 passed` (red after legacy-metrics guard), then
    `6 passed` (green), then `1 failed, 6 passed` (red after watchdog-fixture
    runtime-import guard), then `7 passed` (green), then
    `1 failed, 7 passed` (red after integration-runtime guard), then
    `8 passed` (green)
  - `@' ... import dpost runtime then ipat runtime ... '@ | python -`
    -> `ok`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py`
    -> `8 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/integration/test_integration.py tests/integration/test_device_integrations.py tests/integration/test_multi_processor_app_flow.py tests/integration/test_extr_haake_safesave.py`
    -> `29 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/unit/core/processing/test_file_process_manager.py tests/migration/test_processing_pipeline_stage_boundaries.py tests/integration/test_multi_processor_app_flow.py`
    -> `55 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/integration/test_integration.py tests/integration/test_device_integrations.py`
    -> `26 passed`
  - Required gates:
    - `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
      -> `2 passed`
    - `python -m pytest -m migration`
      -> `169 passed, 302 deselected`
    - `python -m ruff check .`
      -> `All checks passed!`
    - `python -m black --check .`
      -> `157 files would be left unchanged`
    - `python -m pytest`
      -> `470 passed, 1 skipped`
