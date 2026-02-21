# Full Legacy Repo Retirement Roadmap

## Goal
- Retire the remaining legacy repository surface under `src/ipat_watchdog/**`
  and converge the project on canonical `dpost` ownership for runtime,
  plugins, tests, and contributor documentation.

## Scope
- In scope:
  - source retirement for legacy package trees
  - migration of legacy-targeted tests/fixtures to canonical dpost ownership
  - packaging and entrypoint cleanup
  - architecture and contributor documentation finalization
- Out of scope:
  - unrelated feature work
  - behavior redesign beyond parity-preserving refactor
  - large one-shot rewrites

## Current Starting Point (2026-02-21)
- Canonical `dpost` runtime decoupling is complete for Phase 9-13.
- Remaining work is repository-wide legacy retirement:
  - `src/ipat_watchdog/**/*.py`: `119` files
  - `ipat_watchdog` references in `tests/**`: `307`
- Inventory source:
  - `docs/reports/archive/20260221-full-legacy-repo-retirement-inventory.md`
- Kickoff progress:
  - migration guard test added:
    `tests/migration/test_full_legacy_repo_retirement_harness.py`
  - shared helper decoupling landed for:
    `tests/helpers/fake_ui.py`, `tests/helpers/fake_sync.py`, and
    `tests/helpers/fake_process_manager.py`, and
    `tests/helpers/fake_processor.py`
  - conftest coupling reduction landed:
    observer monkeypatch target now resolves from
    `DeviceWatchdogApp.__module__` instead of a hardcoded legacy literal.
  - conftest/runtime fixture migration increment landed:
    shared `watchdog_app` fixture and related unit app test imports now resolve
    `DeviceWatchdogApp` from `dpost.application.runtime.device_watchdog_app`.
  - integration runtime migration increment landed:
    runtime app imports and observer patch targets were migrated to canonical
    dpost runtime ownership in:
    - `tests/integration/test_integration.py`
    - `tests/integration/test_multi_processor_app_flow.py`
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
  - integration legacy-import retirement increment landed:
    integration suites now resolve canonical dpost config/processing/storage/
    plugin boundaries in:
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
    - `tests/integration/test_integration.py`
    - `tests/integration/test_multi_device_integration.py`
    - `tests/integration/test_multi_processor_app_flow.py`
    - `tests/integration/test_settings_integration.py`
    - `tests/integration/test_utm_zwick_integration.py`
  - migration guard scope expanded:
    `tests/migration/test_full_legacy_repo_retirement_harness.py` now enforces
    integration-wide prohibition of `ipat_watchdog` imports.
  - core data-flow unit migration increment landed:
    records/storage/session/sync unit suites now resolve canonical dpost
    boundaries in:
    - `tests/unit/core/records/test_local_record.py`
    - `tests/unit/core/records/test_record_manager.py`
    - `tests/unit/core/session/test_session_manager.py`
    - `tests/unit/core/storage/test_filesystem_utils.py`
    - `tests/unit/core/sync/test_sync_kadi.py`
  - migration guard scope expanded again:
    retirement harness now enforces core data-flow unit prohibition of
    `ipat_watchdog` imports for those suites.
  - core processing/settings unit migration increment landed:
    processing + config/settings unit suites now resolve canonical dpost
    boundaries in:
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
  - migration guard scope expanded again:
    retirement harness now enforces processing/settings unit prohibition of
    `ipat_watchdog` imports for those suites.
  - remaining harness/manual/UI/device test import sweep landed:
    - `tests/conftest.py`
    - `tests/manual/test_plugin_import.py`
    - `tests/manual/test_sync_integration.py`
    - `tests/unit/core/app/test_bootstrap.py`
    - `tests/unit/core/ui/test_dialogs.py`
    - `tests/unit/core/ui/test_ui_tkinter.py`
    - `tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py`
    - `tests/unit/device_plugins/test_device_loader.py`
  - migration-test import sweep landed:
    - `tests/migration/test_processing_pipeline_stage_boundaries.py`
    - `tests/migration/test_naming_constants_consolidation.py`
    - `tests/migration/test_plugin_discovery_hardening.py`
  - migration guard scope expanded again:
    retirement harness now enforces remaining harness/manual/UI/device test
    prohibition of `ipat_watchdog` imports.
  - observability unit migration increment landed:
    `tests/unit/test_observability.py` now imports canonical
    `dpost.infrastructure.observability`.
  - loader/plugin unit migration increment landed:
    - `tests/unit/loader/test_pc_device_mapping.py` now imports
      `dpost.plugins.loading.get_devices_for_pc`
    - `tests/unit/plugins/test_test_plugins_integration.py` now imports
      canonical dpost test plugin modules/settings.
    - `tests/unit/plugin_system/test_plugin_loader.py` and
      `tests/unit/plugin_system/test_no_double_logging.py` now import canonical
      dpost plugin system ownership (`dpost.plugins.system`).
    - `tests/unit/pc_plugins/test_pc_plugins.py`,
      `tests/unit/pc_plugins/test_test_pc_plugin.py`, and
      `tests/unit/pc_plugins/test_haake_pc_plugin.py` now import canonical
      dpost plugin modules/contracts/loading boundaries.
  - device-plugin unit migration increment landed:
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
  - conftest runtime-service bridge was retired after migration-test
    import ownership moved to canonical dpost modules.
  - legacy metrics compatibility boundary landed:
    `src/ipat_watchdog/metrics.py` now re-exports canonical
    `dpost.application.metrics` symbols instead of defining duplicate
    collectors.
  - test import migration now uses canonical dpost module ownership for
    shared fixtures + migration/integration/unit/manual suites.
  - full legacy source retirement checkpoint landed:
    - removed `src/ipat_watchdog/**` (core/runtime/plugins/loader/metrics/
      observability legacy package tree)
    - migration harness now enforces legacy source package absence and native
      `dpost.application.metrics` ownership
    - phase-8 identity guard now validates install guidance from
      `src/dpost/plugins/system.py` instead of removed legacy plugin system.

## Current Status (Post-Retirement Checkpoint)
- `src/ipat_watchdog/**` has been removed from source control.
- Canonical runtime/test paths execute from `src/dpost/**` only.
- Release communication closure is captured in:
  `docs/reports/archive/20260221-full-legacy-retirement-migration-notes.md`.
- Consolidated operator closure steps are captured in:
  `docs/checklists/archive/20260221-final-manual-validation-runbook.md`.
- Remaining retirement work is manual validation only, not additional source
  migration.

## End-State Definition
- `dpost` is the only canonical runtime/import target.
- No required production path depends on `src/ipat_watchdog/**`.
- Legacy test suite is either:
  - fully migrated to canonical dpost imports/contracts, or
  - intentionally archived with explicit non-gating status and rationale.
- Architecture/docs/testing guidance is canonical-dpost only.

## Execution Principles
- Tests-first slices (red -> green -> refactor) for behavior-affecting changes.
- Preserve behavior parity for startup, processing, routing, record persistence,
  sync side effects, and operator-visible errors.
- Keep changes incremental and checkpoint-committed.
- Update docs/governance artifacts in the same change set as architecture work.

## Phase Plan
1. Retirement Baseline Freeze
- Lock inventory and target state.
- Add migration guards for global retirement criteria.

2. Test Harness Canonicalization
- Migrate shared test fixtures/helpers from legacy imports to dpost boundaries.
- Remove `ipat_watchdog` imports from migration tests first, then unit/
  integration/manual tests.

3. Plugin Surface Retirement
- Ensure all plugin tests and loading paths resolve through `src/dpost/**`.
- Retire `src/ipat_watchdog/device_plugins/**` and
  `src/ipat_watchdog/pc_plugins/**` in bounded slices.

4. Core Runtime Surface Retirement
- Retire remaining legacy core modules (`core/app`, `core/processing`,
  `core/records`, `core/sync`, `core/config`, `core/storage`, `core/ui`)
  after test ownership is migrated.

5. Packaging and Entrypoint Cleanup
- Remove legacy package metadata references and stale naming hints.
- Keep only canonical script/module startup targets.

6. Documentation and OSS Hardening
- Finalize architecture baseline/contract/responsibility/ADR alignment.
- Finalize contributor docs for extension/testing/runtime workflows.
- Publish migration notes for downstream users.

7. Final Deletion Sweep and Validation
- Remove any residual dead compatibility artifacts.
- Run full required gates + manual validation checklist.
- Capture closure report with residual risk set to zero or explicit exceptions.

## Required Gates (Each Slice)
- `python -m pytest tests/migration/<slice>.py`
- `python -m pytest -m migration`
- `python -m ruff check .`
- `python -m black --check .`
- `python -m pytest`

## Risks and Mitigations
- Risk: hidden legacy coupling in tests.
  - Mitigation: import-sweep guards and fixture-by-fixture migration.
- Risk: behavior drift while deleting legacy modules.
  - Mitigation: red/green parity tests for each deleted capability slice.
- Risk: contributor confusion during transition.
  - Mitigation: keep roadmap/checklist/report and developer docs synchronized.

## Rollout
- Execute as checkpointed autonomous slices.
- Keep progress evidence in:
  - `docs/reports/archive/20260221-full-legacy-repo-retirement-inventory.md`
  - `docs/reports/archive/20260221-phase10-13-runtime-boundary-progress.md`
  - new retirement progress reports as slices land.

