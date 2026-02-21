# Architecture Baseline (Current State)

## Snapshot Date
- 2026-02-21 (updated through full `src/ipat_watchdog/**` source retirement)

## System Purpose
- Monitor local watch directories for instrument output.
- Route artifacts through device-specific processing.
- Persist local record state.
- Synchronize records/files to an external ELN/database backend.

## High-level Runtime Flow
1. Entrypoint starts bootstrap and resolves startup settings.
2. Bootstrap loads PC + device plugin configuration and initializes services.
3. Filesystem observer enqueues events.
4. App loop drains queue through the processing pipeline.
5. Processing pipeline resolves device, stabilizes artifact, preprocesses, routes, and records outputs.
6. Record manager persists state and triggers sync backend.

## Layer Intent (Targeting dpost Direction)
- Domain:
- data models and pure business rules
- Application:
- orchestration and use-case execution
- Infrastructure:
- filesystem, sync adapters, observability, UI/runtime adapters
- Plugins:
- device and PC extension points

## Current Key Components
- Bootstrap and startup wiring:
- `src/dpost/runtime/bootstrap.py`
- Runtime bootstrap infrastructure dependencies boundary:
- `src/dpost/infrastructure/runtime/bootstrap_dependencies.py`
- New migration composition scaffold:
- `src/dpost/runtime/composition.py`
- Runtime orchestration application service:
- `src/dpost/application/services/runtime_startup.py`
- Runtime startup config boundary:
- `src/dpost/runtime/startup_config.py`
- Plugin profile selection boundary:
- `src/dpost/plugins/profile_selection.py`
- Plugin loading boundary + plugin contracts:
- `src/dpost/plugins/loading.py`
- `src/dpost/plugins/system.py`
- `src/dpost/plugins/contracts.py`
- dpost composition now validates selected sync adapter and injects a
  `sync_manager_factory` into runtime bootstrap wiring through
  `dpost.application.services.runtime_startup`.
- dpost composition now supports an explicit reference plugin profile path via
  `DPOST_PLUGIN_PROFILE=reference`, mapping to startup settings without direct
  concrete plugin/backend coupling.
- dpost runtime startup config boundary now resolves optional
  `DPOST_PC_NAME`, `DPOST_DEVICE_PLUGINS`, `DPOST_PROMETHEUS_PORT`, and
  `DPOST_OBSERVABILITY_PORT` overrides before runtime bootstrap.
- dpost composition now includes explicit runtime mode selection via
  `DPOST_RUNTIME_MODE` (`headless` default, `desktop` optional) and validates
  unknown runtime mode values at startup.
- Runtime UI factory infrastructure adapter now resolves explicit mode-specific
  UI factories (`HeadlessRuntimeUI` for headless mode, `TKinterRuntimeUI` for
  desktop mode).
- dpost headless runtime UI adapter:
- `src/dpost/infrastructure/runtime/headless_ui.py`
- dpost runtime UI factory adapter:
- `src/dpost/infrastructure/runtime/ui_factory.py`
- dpost runtime desktop UI boundary:
- `src/dpost/infrastructure/runtime/desktop_ui.py`
- dpost runtime desktop UI implementation:
- `src/dpost/infrastructure/runtime/tkinter_ui.py`
- dpost runtime desktop rename-dialog boundary:
- `src/dpost/infrastructure/runtime/dialogs.py`
- dpost runtime UI adapters boundary:
- `src/dpost/infrastructure/runtime/ui_adapters.py`
- dpost canonical logging infrastructure:
- `src/dpost/infrastructure/logging.py`
- dpost observability infrastructure:
- `src/dpost/infrastructure/observability.py`
- dpost sync adapter port contract:
- `src/dpost/application/ports/sync.py`
- dpost runtime UI port contract:
- `src/dpost/application/ports/ui.py`
- dpost runtime interaction port contract:
- `src/dpost/application/ports/interactions.py`
- dpost runtime interaction message catalog:
- `src/dpost/application/interactions/messages.py`
- dpost reference sync adapter (noop):
- `src/dpost/infrastructure/sync/noop.py`
- dpost reference plugin profile contract:
- `src/dpost/plugins/reference.py`
- dpost Kadi sync adapter wrapper (optional backend):
- `src/dpost/infrastructure/sync/kadi.py`
- dpost packaging split for optional Kadi backend dependency:
- `pyproject.toml` (`[project.optional-dependencies].kadi`)
- Runtime loop and event handling:
- `src/dpost/application/runtime/device_watchdog_app.py`
- Transition dependency shim retirement:
- `src/dpost/application/runtime/runtime_dependencies.py` (retired)
- `src/dpost/infrastructure/runtime/config_dependencies.py` (retired)
- Processing orchestration:
- `src/dpost/application/processing/file_process_manager.py`
- dpost processing helper module set:
- `src/dpost/application/processing/`
- dpost processing batch/staging/text helpers:
- `src/dpost/application/processing/batch_models.py`
- `src/dpost/application/processing/staging_utils.py`
- `src/dpost/application/processing/text_utils.py`
- Phase 5 decomposition status:
- `_ProcessingPipeline` now exposes explicit resolve/stabilize/preprocess stage
  hooks (`_resolve_device_stage`, `_stabilize_artifact_stage`,
  `_preprocess_stage`), an explicit route-decision stage hook
  (`_route_decision_stage`), an explicit non-ACCEPT route stage hook
  (`_non_accept_route_stage`), and an explicit persist/sync stage hook
  (`_persist_and_sync_stage`) on ACCEPT routing paths.
- `FileProcessManager` now exposes `_persist_candidate_record_stage()` and
  `_persist_and_sync_stage()` delegates ACCEPT persistence through this seam.
- `FileProcessManager` now exposes
  `_resolve_record_processor_stage()` and `add_item_to_record()` delegates
  processor selection through this seam.
- `FileProcessManager` now exposes
  `_resolve_record_persistence_context_stage()` and `add_item_to_record()`
  delegates record/processor/path-id setup through this seam.
- `FileProcessManager` now exposes `_process_record_artifact_stage()` and
  `add_item_to_record()` delegates processor invocation/output handling
  through this seam.
- `FileProcessManager` now exposes `_assign_record_datatype_stage()` and
  `add_item_to_record()` delegates datatype assignment through this seam.
- `FileProcessManager` now exposes `_finalize_record_output_stage()` and
  `add_item_to_record()` delegates output finalization through this seam.
- `FileProcessManager` now exposes `_post_persist_side_effects_stage()` and
  `add_item_to_record()` delegates bookkeeping/metrics/immediate-sync side
  effects through this seam.
- Transition-only `_ProcessingPipeline._prepare_request()` helper has been
  retired from canonical dpost processing paths.
- `add_item_to_record()` no longer exposes the legacy `notify` flag and no
  longer dispatches the legacy success-notification helper.
- `_invoke_rename_flow()` now uses iterative retry evaluation, removing
  recursive `_route_with_prefix()` re-entry during non-ACCEPT rename loops.
- `_rename_retry_policy_stage()` now defines non-ACCEPT retry warning/context
  policy for the rename loop.
- Plugin loading and registration:
- `src/dpost/plugins/system.py`
- Canonical reference plugin packages for migration/runtime validation:
- `src/dpost/device_plugins/test_device/`
- `src/dpost/pc_plugins/test_pc/`
- Canonical concrete plugin package (migration wave):
- `src/dpost/device_plugins/utm_zwick/`
- `src/dpost/device_plugins/extr_haake/`
- `src/dpost/device_plugins/erm_hioki/`
- `src/dpost/device_plugins/sem_phenomxl2/`
- `src/dpost/device_plugins/rmx_eirich_el1/`
- `src/dpost/device_plugins/rmx_eirich_r01/`
- `src/dpost/device_plugins/dsv_horiba/`
- `src/dpost/device_plugins/rhe_kinexus/`
- `src/dpost/device_plugins/psa_horiba/`
- Canonical concrete PC plugin package (migration wave):
- `src/dpost/pc_plugins/zwick_blb/`
- `src/dpost/pc_plugins/haake_blb/`
- `src/dpost/pc_plugins/hioki_blb/`
- `src/dpost/pc_plugins/tischrem_blb/`
- `src/dpost/pc_plugins/eirich_blb/`
- `src/dpost/pc_plugins/horiba_blb/`
- `src/dpost/pc_plugins/kinexus_blb/`
- dpost storage utility boundary:
- `src/dpost/infrastructure/storage/filesystem_utils.py`
- Configuration schema and runtime service:
- `src/dpost/application/config/`
- dpost metrics boundary:
- `src/dpost/application/metrics.py`
- Local record persistence:
- `src/dpost/application/records/`
- Current Kadi backend implementation:
- `src/dpost/infrastructure/sync/kadi_manager.py`

## Current Test Isolation Baseline
- Pytest markers enforce split test intent:
- `legacy` marker reserved for archived compatibility characterization suites.
- `migration` marker for `dpost` migration and cutover tests.
- New migration entrypoint tests currently live in:
- `tests/migration/test_dpost_main.py`
- Phase 3 sync adapter selection tests currently live in:
- `tests/migration/test_sync_adapter_selection.py`
- Phase 3 optional Kadi packaging contract test currently lives in:
- `tests/migration/test_optional_kadi_packaging.py`
- Phase 3 reference plugin flow test currently lives in:
- `tests/migration/test_reference_plugin_flow.py`
- Phase 4 config consolidation tests currently live in:
- `tests/migration/test_configuration_consolidation.py`
- Phase 4 naming/constants consolidation tests currently live in:
- `tests/migration/test_naming_constants_consolidation.py`
- Phase 5 stage-boundary decomposition tests currently live in:
- `tests/migration/test_processing_pipeline_stage_boundaries.py`
- Phase 7 runtime mode + desktop parity tests currently live in:
- `tests/migration/test_runtime_mode_selection.py`
- Phase 9 native runtime bootstrap boundary tests currently live in:
- `tests/migration/test_phase9_native_bootstrap_boundary.py`
- Phase 10 application orchestration extraction tests currently live in:
- `tests/migration/test_phase10_application_orchestration_extraction.py`
- Phase 10 runtime app rehost tests currently live in:
- `tests/migration/test_phase10_runtime_app_rehost.py`
- Phase 11 runtime infrastructure boundary tests currently live in:
- `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
- Phase 12 plugin/config boundary migration tests currently live in:
- `tests/migration/test_phase12_plugin_config_boundary_migration.py`
- Phase 12 plugin loading ownership tests currently live in:
- `tests/migration/test_phase12_plugin_loading_ownership.py`
- Phase 13 canonical startup retirement tests currently live in:
- `tests/migration/test_phase13_legacy_runtime_retirement.py`
- Phase 13 native bootstrap service retirement tests currently live in:
- `tests/migration/test_phase13_native_bootstrap_service_retirement.py`

## Notable Constraints in Current Baseline
- Some global/singleton patterns are still present in runtime wiring.
- Operational config/naming paths now use strict fail-fast behavior when
  config service is not initialized.
- dpost composition default runtime mode is now explicit headless, with
  optional desktop mode wiring.
- Sync backend is currently Kadi-coupled in core paths.
- dpost runtime bootstrap is now native and no longer delegates through a
  transition bootstrap adapter.
- Canonical startup modules no longer import `ipat_watchdog.core` directly,
  and no infrastructure adapters delegate to legacy runtime modules.
- Canonical startup modules also avoid direct `ipat_watchdog.observability`
  imports and resolve observability through `dpost.infrastructure`.
- Canonical runtime app/bootstrap modules now route config/session/metrics
  dependencies through dedicated dpost boundary modules, and no longer import
  legacy processing/storage modules directly in canonical dpost processing
  paths.
- Canonical dpost config and metrics boundaries are now dpost-owned and no
  longer import legacy config/metrics modules directly.
- Transition runtime dependency shims have been retired from canonical dpost
  paths (`runtime_dependencies.py`, `config_dependencies.py`).
- dpost plugin profile support remains reference-first for kernel validation.
- dpost plugin loading now uses dpost-owned plugin protocol contracts;
  canonical plugin discovery groups now use `dpost.device_plugins` and
  `dpost.pc_plugins` with no legacy namespace fallback mappings in canonical
  dpost paths.
- Canonical reference profile plugins (`test_device`, `test_pc`) now load from
  dpost plugin namespaces before any legacy fallback path.
- Concrete UTM Zwick plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.utm_zwick`) before any legacy fallback path.
- Concrete EXTR HAAKE plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.extr_haake`) before any legacy fallback path.
- Concrete ERM HIOKI plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.erm_hioki`) before any legacy fallback path.
- Concrete SEM PHENOM XL2 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.sem_phenomxl2`) before any legacy fallback path.
- Concrete RMX EIRICH EL1 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rmx_eirich_el1`) before any legacy fallback path.
- Concrete RMX EIRICH R01 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rmx_eirich_r01`) before any legacy fallback path.
- Concrete DSV HORIBA plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.dsv_horiba`) before any legacy fallback path.
- Concrete RHE KINEXUS plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rhe_kinexus`) before any legacy fallback path.
- Concrete PSA HORIBA plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.psa_horiba`) before any legacy fallback path.
- Concrete Zwick BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.zwick_blb`) before any legacy fallback path.
- Concrete HAAKE BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.haake_blb`) before any legacy fallback path.
- Concrete HIOKI BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.hioki_blb`) before any legacy fallback path.
- Concrete TISCHREM BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.tischrem_blb`) before any legacy fallback path.
- Concrete EIRICH BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.eirich_blb`) before any legacy fallback path.
- Concrete HORIBA BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.horiba_blb`) before any legacy fallback path.
- Concrete KINEXUS BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.kinexus_blb`) before any legacy fallback path.
- dpost plugin loading now uses canonical hook namespace marker `dpost` and
  no longer orchestrates legacy hook namespaces in canonical dpost paths.
- Canonical extension contracts are now explicitly documented in
  `docs/architecture/extension-contracts.md`; `DevicePlugin` contract
  expectations include both configuration access and file-processor access.
- Legacy source package `src/ipat_watchdog/` is retired from the repository.
- Rename retries no longer recurse through `_route_with_prefix()`, but rename
  prompts and retry loop orchestration still live in `file_process_manager`
  and remain active decomposition targets.
- `add_item_to_record()` now delegates record-context resolution, processor
  selection, invocation, datatype assignment, output finalization, and
  post-persist side effects; stage-call ordering remains coupled there and is
  an active decomposition target.

## Migration Notes
- Headless-first migration is the current execution posture.
- Framework-first sequencing is active: kernel and contracts are prioritized before concrete integrations.
- Sync is being moved toward optional adapter architecture for multi-ELN/database support.
- Default `dpost` install path no longer requires `kadi_apy`; Kadi is enabled via
  the `kadi` optional dependency group.
- Major structural updates should be tracked via ADRs in `docs/architecture/adr/`.
