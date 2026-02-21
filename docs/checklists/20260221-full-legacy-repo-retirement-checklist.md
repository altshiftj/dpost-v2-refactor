# Full Legacy Repo Retirement Checklist

## Section: Baseline and Governance Freeze
- Why this matters: Retirement without a locked baseline risks deleting
  capabilities that are still operationally required.

### Checklist
- [x] Capture legacy repository inventory and reference counts.
- [x] Define retirement target end-state criteria.
- [x] Add migration guard tests for repository-wide retirement criteria.
- [x] Link roadmap/checklist/report artifacts from active contributor docs.
- [x] Define explicit exception policy for any temporary retained legacy files.

### Completion Notes
- How it was done: Inventory baseline captured in
  `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`.
  Migration guard coverage started in
  `tests/migration/test_full_legacy_repo_retirement_harness.py` with explicit
  assertions for shared helper decoupling from legacy interaction/sync imports.
  Roadmap/checklist/report artifacts are linked from canonical contributor docs
  (`README.md`, `DEVELOPER_README.md`).
  Exception policy is now explicit: no temporary retained legacy source files
  are permitted under `src/ipat_watchdog/**`.

---

## Section: Test Harness Canonicalization
- Why this matters: Legacy tests are the largest remaining coupling surface and
  must migrate before safe source deletion.

### Checklist
- [x] Migrate shared fixtures in `tests/conftest.py` and `tests/helpers/**` to
      canonical dpost imports.
- [x] Remove `ipat_watchdog` imports from migration tests.
- [x] Remove `ipat_watchdog` imports from unit tests.
- [x] Remove `ipat_watchdog` imports from integration tests.
- [x] Remove `ipat_watchdog` imports from manual tests.
- [x] Keep migration/full gates green during each test migration slice.

### Completion Notes
- How it was done: Completed. Shared helper interfaces were migrated from
  legacy imports in:
  - `tests/helpers/fake_ui.py`
  - `tests/helpers/fake_sync.py`
  - `tests/helpers/fake_process_manager.py`
  - `tests/helpers/fake_processor.py`
  - canonical metrics ownership is now enforced in
    `src/dpost/application/metrics.py` after full legacy source retirement.
  Conftest follow-up now includes:
  - hardcoded legacy observer monkeypatch literal removal
  - watchdog fixture migration to
    `dpost.application.runtime.device_watchdog_app.DeviceWatchdogApp`
  - matching unit app test import migration in
    `tests/unit/core/app/test_device_watchdog_app.py`
  - runtime app import migration for integration suites:
    - `tests/integration/test_integration.py`
    - `tests/integration/test_multi_processor_app_flow.py`
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
  - observer patch target migration to dynamic module resolution in those
    integration suites
  - explicit legacy processing manager injection retained in
    `test_device_integrations.py` and `test_extr_haake_safesave.py` to preserve
    existing behavior while runtime/config convergence continues
  - observability unit test migration to canonical dpost infrastructure module:
    - `tests/unit/test_observability.py`
  - loader/plugin unit migration to canonical dpost plugin loading boundaries:
    - `tests/unit/loader/test_pc_device_mapping.py`
    - `tests/unit/plugins/test_test_plugins_integration.py`
    - `tests/unit/plugin_system/test_plugin_loader.py`
    - `tests/unit/plugin_system/test_no_double_logging.py`
    - `tests/unit/pc_plugins/test_pc_plugins.py`
    - `tests/unit/pc_plugins/test_test_pc_plugin.py`
    - `tests/unit/pc_plugins/test_haake_pc_plugin.py`
  - device-plugin unit migration to canonical dpost plugin modules:
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
  - runtime-service fixture bridge in conftest now seeds both legacy and dpost
    runtime registries so mixed-import test slices remain behaviorally aligned
    while import retirement continues.
  - integration suite migration to canonical dpost boundaries:
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
    - `tests/integration/test_integration.py`
    - `tests/integration/test_multi_device_integration.py`
    - `tests/integration/test_multi_processor_app_flow.py`
    - `tests/integration/test_settings_integration.py`
    - `tests/integration/test_utm_zwick_integration.py`
  - migration harness now includes integration-wide retirement guard:
    `test_integration_tests_avoid_legacy_import_paths`.
  - core data-flow unit suite migration to canonical dpost boundaries:
    - `tests/unit/core/records/test_local_record.py`
    - `tests/unit/core/records/test_record_manager.py`
    - `tests/unit/core/session/test_session_manager.py`
    - `tests/unit/core/storage/test_filesystem_utils.py`
    - `tests/unit/core/sync/test_sync_kadi.py`
  - migration harness now includes core data-flow unit retirement guard:
    `test_core_dataflow_unit_tests_avoid_legacy_import_paths`.
  - core processing/settings unit suite migration to canonical dpost
    boundaries:
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
  - migration harness now includes processing/settings unit retirement guard:
    `test_core_processing_and_settings_unit_tests_avoid_legacy_import_paths`.
  - remaining harness/manual/UI/device import sweep to canonical dpost
    ownership:
    - `tests/conftest.py`
    - `tests/manual/test_plugin_import.py`
    - `tests/manual/test_sync_integration.py`
    - `tests/unit/core/app/test_bootstrap.py`
    - `tests/unit/core/ui/test_dialogs.py`
    - `tests/unit/core/ui/test_ui_tkinter.py`
    - `tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py`
    - `tests/unit/device_plugins/test_device_loader.py`
  - migration test import sweep to canonical dpost ownership:
    - `tests/migration/test_processing_pipeline_stage_boundaries.py`
    - `tests/migration/test_naming_constants_consolidation.py`
    - `tests/migration/test_plugin_discovery_hardening.py`
  - migration harness now includes remaining import sweep guard:
    `test_remaining_test_import_sweep_avoids_legacy_import_paths`.

---

## Section: Plugin Package Retirement
- Why this matters: Full retirement requires eliminating duplicated plugin
  trees and converging tests/imports on canonical dpost plugins.

### Checklist
- [x] Confirm all plugin loaders/tests resolve canonical dpost plugin paths.
- [x] Retire `src/ipat_watchdog/device_plugins/**` in bounded slices.
- [x] Retire `src/ipat_watchdog/pc_plugins/**` in bounded slices.
- [x] Remove stale legacy plugin-specific docs and naming references.
- [x] Verify plugin loading/actionability parity after each slice.

### Completion Notes
- How it was done: Canonical plugin loading/tests already resolved to
  `src/dpost/**`, then full legacy source retirement removed the mirrored
  plugin trees and loader/plugin-system modules under `src/ipat_watchdog/**`.
  Migration guard coverage now enforces absence of the legacy source package
  root and keeps plugin-loading ownership checks green.

---

## Section: Core Package Retirement
- Why this matters: Legacy core module deletion is the decisive step to remove
  dual-architecture maintenance burden.

### Checklist
- [x] Retire `src/ipat_watchdog/core/app/**` after canonical test migration.
- [x] Retire `src/ipat_watchdog/core/processing/**` after parity tests remain green.
- [x] Retire `src/ipat_watchdog/core/records/**` and `core/sync/**` after parity checks.
- [x] Retire `src/ipat_watchdog/core/config/**`, `core/storage/**`, and `core/ui/**`.
- [x] Remove residual legacy package exports and dead imports.

### Completion Notes
- How it was done: Full legacy source package deletion retired all remaining
  core trees under `src/ipat_watchdog/core/**`; canonical runtime,
  processing, records, config, storage, UI, and sync boundaries are now owned
  by `src/dpost/**`.

---

## Section: Packaging and Documentation Finalization
- Why this matters: Packaging/docs must match the real architecture so
  contributors and users do not follow stale legacy paths.

### Checklist
- [x] Remove legacy package metadata/entrypoint references from `pyproject.toml`.
- [x] Ensure README/USER/DEVELOPER docs are canonical-dpost only.
- [x] Update architecture baseline/contract/responsibility and ADR trail.
- [x] Update `GLOSSARY.csv` for retirement terminology changes.
- [x] Capture final retirement closure report with exact gate evidence.

### Completion Notes
- How it was done:
  - `pyproject.toml` no longer contains legacy package-name references and
    legacy Black exclusion for `src/ipat_watchdog/`.
  - `DEVELOPER_README.md` and architecture guide wording now describe
    canonical dpost ownership and archived `legacy` marker posture.
  - Architecture governance artifacts were updated:
    - `docs/architecture/architecture-baseline.md`
    - `docs/architecture/architecture-contract.md`
    - `docs/architecture/responsibility-catalog.md`
    - `docs/architecture/adr/ADR-0004-full-legacy-source-package-retirement.md`
  - `GLOSSARY.csv` remains valid without new internal-term additions for this
    slice.
  - retirement gate evidence captured in
    `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`.
  - downstream migration/release communication captured in
    `docs/reports/20260221-full-legacy-retirement-migration-notes.md`.

---

## Section: Manual Check
- Why this matters: Human workflow checks validate operator-facing behavior
  that can still regress despite broad automated coverage.

### Checklist
- [ ] Desktop runtime manual check after legacy package deletion.
- [ ] Headless runtime manual check after legacy package deletion.
- [ ] Plugin family spot checks across representative instruments.
- [ ] Records/sync side-effect check with a failing-sync scenario.
- [ ] Contributor usability check: docs are sufficient without legacy tracing.

### Manual Validation Steps
1. Run `python -m dpost` in `desktop` mode and process valid/invalid files.
2. Run `python -m dpost` in `headless` mode and verify processing + endpoints.
3. Execute representative plugin workloads and one unknown-plugin failure path.
4. Validate local record persistence and sync retry/error behavior.
5. Perform a cold-read of contributor docs and extension contracts.

### Completion Notes
- How it was done: Automated prechecks were executed (`tests/manual/`
  automation path + `tests/manual/test_plugin_import.py` script run with ASCII
  console-safe output), while human operator workflow checks remain pending.
  Consolidated operator steps are captured in:
  `docs/checklists/20260221-final-manual-validation-runbook.md`.
