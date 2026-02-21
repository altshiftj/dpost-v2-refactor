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
  - `docs/planning/archive/20260221-dpost-full-legacy-decoupling-clean-architecture-roadmap.md`
  - `docs/checklists/archive/20260221-dpost-full-legacy-decoupling-clean-architecture-checklist.md`
  - `docs/reports/archive/20260221-phase10-13-runtime-boundary-progress.md`
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
- Migration notes:
  - `docs/reports/20260221-full-legacy-retirement-migration-notes.md`

## Progress Update (Closure Hardening)
- Added manual-script portability migration guard:
  - `tests/migration/test_manual_script_portability.py`
- Updated manual plugin import helper to ASCII-safe output markers for default
  Windows console compatibility:
  - `tests/manual/test_plugin_import.py`
- Captured downstream release communication/migration guidance in:
  - `docs/reports/20260221-full-legacy-retirement-migration-notes.md`

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
- Migrated observability unit tests to canonical dpost infrastructure module:
  - `tests/unit/test_observability.py`
- Migrated selected loader/plugin unit tests to canonical dpost modules:
  - `tests/unit/loader/test_pc_device_mapping.py`
  - `tests/unit/plugins/test_test_plugins_integration.py`
  - `tests/unit/plugin_system/test_plugin_loader.py`
  - `tests/unit/plugin_system/test_no_double_logging.py`
  - `tests/unit/pc_plugins/test_pc_plugins.py`
  - `tests/unit/pc_plugins/test_test_pc_plugin.py`
  - `tests/unit/pc_plugins/test_haake_pc_plugin.py`
- Migrated selected device-plugin unit tests to canonical dpost modules:
  - `tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py`
  - `tests/unit/device_plugins/erm_hioki/test_file_processor.py`
  - `tests/unit/device_plugins/extr_haake/test_plugin.py`
  - `tests/unit/device_plugins/mix_eirich/test_file_processor.py`
  - `tests/unit/device_plugins/psa_horiba/test_file_processor.py`
  - `tests/unit/device_plugins/psa_horiba/test_purge_and_reconstruct.py`
  - `tests/unit/device_plugins/psa_horiba/test_staging_rename_cancel.py`
  - `tests/unit/device_plugins/rhe_kinexus/test_file_processor.py`
  - `tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py`
  - `tests/unit/device_plugins/utm_zwick/test_file_processor.py`
- Added runtime-service bridge in shared test fixture:
  - `tests/conftest.py` now registers the fixture-created config service with
    both legacy and dpost runtime registries and resets both during teardown.
- Retired temporary runtime-service bridge after migration-test import ownership
  moved to canonical dpost modules:
  - `tests/conftest.py` now uses canonical dpost config/storage imports only.
- Added integration-wide legacy-import retirement guard:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py` now asserts
    all integration tests avoid `ipat_watchdog` import paths.
- Migrated integration suites to canonical dpost boundaries:
  - `tests/integration/test_device_integrations.py`
  - `tests/integration/test_extr_haake_safesave.py`
  - `tests/integration/test_integration.py`
  - `tests/integration/test_multi_device_integration.py`
  - `tests/integration/test_multi_processor_app_flow.py`
  - `tests/integration/test_settings_integration.py`
  - `tests/integration/test_utm_zwick_integration.py`
- Added core data-flow unit legacy-import retirement guard:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py` now asserts
    selected records/storage/session/sync unit suites avoid
    `ipat_watchdog` import paths.
- Migrated core data-flow unit suites to canonical dpost boundaries:
  - `tests/unit/core/records/test_local_record.py`
  - `tests/unit/core/records/test_record_manager.py`
  - `tests/unit/core/session/test_session_manager.py`
  - `tests/unit/core/storage/test_filesystem_utils.py`
  - `tests/unit/core/sync/test_sync_kadi.py`
- Added core processing/settings unit legacy-import retirement guard:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py` now asserts
    selected processing/settings unit suites avoid `ipat_watchdog`
    import paths.
- Migrated core processing/settings unit suites to canonical dpost boundaries:
  - `tests/unit/core/processing/test_device_resolver.py`
  - `tests/unit/core/processing/test_device_resolver_eirich_variants.py`
  - `tests/unit/core/processing/test_error_handling.py`
  - `tests/unit/core/processing/test_file_process_manager.py`
  - `tests/unit/core/processing/test_force_paths_kadi_sync.py`
  - `tests/unit/core/processing/test_modified_event_gate.py`
  - `tests/unit/core/processing/test_stability_tracker.py`
  - `tests/unit/core/settings/test_composite_settings.py`
  - `tests/unit/core/settings/test_device_settings_base.py`
  - `tests/unit/core/settings/test_settings_classes.py`
  - `tests/unit/core/settings/test_settings_manager.py`
  - `tests/unit/core/settings/test_stability_tracker_overrides.py`
- Added remaining import-sweep legacy-retirement guard:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py` now asserts
    selected conftest/manual/core-ui/core-app/device-loader suites avoid
    `ipat_watchdog` import paths.
- Migrated remaining conftest/manual/core-ui/core-app/device-loader tests to
  canonical dpost boundaries:
  - `tests/conftest.py`
  - `tests/manual/test_plugin_import.py`
  - `tests/manual/test_sync_integration.py`
  - `tests/unit/core/app/test_bootstrap.py`
  - `tests/unit/core/ui/test_dialogs.py`
  - `tests/unit/core/ui/test_ui_tkinter.py`
  - `tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py`
  - `tests/unit/device_plugins/test_device_loader.py`
- Migrated remaining migration suites with direct legacy imports to canonical
  dpost boundaries:
  - `tests/migration/test_processing_pipeline_stage_boundaries.py`
  - `tests/migration/test_naming_constants_consolidation.py`
  - `tests/migration/test_plugin_discovery_hardening.py`
- Retired direct Prometheus collector definitions from legacy metrics module:
  - `src/ipat_watchdog/metrics.py` now re-exports canonical
    `dpost.application.metrics` symbols.
- Retired full legacy source package tree:
  - removed `src/ipat_watchdog/**` including legacy `core/`, plugin trees,
    `loader.py`, `plugin_system.py`, `metrics.py`, and `observability.py`.
- Updated migration guards for post-retirement end state:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py` now requires
    `src/ipat_watchdog/` package absence and verifies canonical
    `src/dpost/application/metrics.py` ownership.
  - `tests/migration/test_phase8_cutover_identity.py` now validates plugin
    install guidance from `src/dpost/plugins/system.py`.
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
    `8 passed` (green), then `1 failed, 8 passed` (red after
    observability-import guard), then `9 passed` (green), then
    `1 failed, 9 passed` (red after loader-plugin guard), then
    `10 passed` (green), then `1 failed, 10 passed` (red after device-plugin
    guard), then `11 passed` (green), then
    `1 failed, 11 passed` (red after integration-import guard), then
    `12 passed` (green), then
    `1 failed, 12 passed` (red after core-dataflow guard), then
    `13 passed` (green), then
    `1 failed, 13 passed` (red after processing-settings guard), then
    `14 passed` (green), then
    `1 failed, 14 passed` (red after remaining-import-sweep guard), then
    `15 passed` (green)
  - `@' ... import dpost runtime then ipat runtime ... '@ | python -`
    -> `ok`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py`
    -> `8 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/integration/test_integration.py tests/integration/test_device_integrations.py tests/integration/test_multi_processor_app_flow.py tests/integration/test_extr_haake_safesave.py`
    -> `29 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/test_observability.py`
    -> `15 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/loader/test_pc_device_mapping.py tests/unit/plugins/test_test_plugins_integration.py`
    -> `31 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/plugin_system/test_plugin_loader.py tests/unit/plugin_system/test_no_double_logging.py tests/unit/pc_plugins/test_pc_plugins.py tests/unit/pc_plugins/test_test_pc_plugin.py tests/unit/pc_plugins/test_haake_pc_plugin.py`
    -> `28 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/device_plugins/extr_haake/test_plugin.py tests/unit/device_plugins/mix_eirich/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_purge_and_reconstruct.py tests/unit/device_plugins/psa_horiba/test_staging_rename_cancel.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py tests/unit/device_plugins/utm_zwick/test_file_processor.py`
    -> `7 failed, 47 passed, 2 errors` (red), then `56 passed` (green)
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/integration/test_integration.py tests/integration/test_multi_device_integration.py tests/integration/test_multi_processor_app_flow.py tests/integration/test_device_integrations.py tests/integration/test_settings_integration.py tests/integration/test_utm_zwick_integration.py tests/integration/test_extr_haake_safesave.py`
    -> `45 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/core/records/test_local_record.py tests/unit/core/records/test_record_manager.py tests/unit/core/storage/test_filesystem_utils.py tests/unit/core/session/test_session_manager.py tests/unit/core/sync/test_sync_kadi.py`
    -> `67 passed, 1 skipped`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/core/processing tests/unit/core/settings`
    -> `83 passed`
  - `python -m pytest tests/migration/test_processing_pipeline_stage_boundaries.py tests/migration/test_naming_constants_consolidation.py tests/migration/test_plugin_discovery_hardening.py tests/migration/test_full_legacy_repo_retirement_harness.py`
    -> `57 passed`
  - `python -m pytest tests/unit/core/ui/test_ui_tkinter.py tests/unit/core/ui/test_dialogs.py tests/unit/core/app/test_bootstrap.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py tests/unit/device_plugins/test_device_loader.py tests/manual/test_sync_integration.py tests/manual/test_plugin_import.py`
    -> `43 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/unit/core/processing/test_file_process_manager.py tests/migration/test_processing_pipeline_stage_boundaries.py tests/integration/test_multi_processor_app_flow.py`
    -> `55 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/integration/test_integration.py tests/integration/test_device_integrations.py`
    -> `26 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py`
    -> `1 failed, 15 passed` (red), then `16 passed` (green)
  - `cmd /c rmdir /s /q src\ipat_watchdog`
    -> completed (legacy source tree removed)
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/migration/test_phase8_cutover_identity.py`
    -> `25 passed`
  - `python -m pytest -m migration`
    -> `177 passed, 302 deselected`
  - Required gates:
    - `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
      -> `2 passed`
    - `python -m pytest -m migration`
      -> `177 passed, 302 deselected`
    - `python -m ruff check .`
      -> `All checks passed!`
    - `python -m black --check .`
      -> `157 files would be left unchanged`
    - `python -m pytest`
      -> `478 passed, 1 skipped`
