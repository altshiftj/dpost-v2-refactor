# Architecture Baseline (Current State)

## Snapshot Date
- 2026-02-21 (updated through Part 3 domain extraction Wave 3.10 staging helper infrastructure ownership)

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
- `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py`
- New runtime composition scaffold:
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
- `src/dpost/infrastructure/runtime_adapters/headless_ui.py`
- dpost runtime UI factory adapter:
- `src/dpost/infrastructure/runtime_adapters/ui_factory.py`
- dpost runtime desktop UI boundary:
- `src/dpost/infrastructure/runtime_adapters/desktop_ui.py`
- dpost runtime desktop UI implementation:
- `src/dpost/infrastructure/runtime_adapters/tkinter_ui.py`
- dpost runtime desktop rename-dialog boundary:
- `src/dpost/infrastructure/runtime_adapters/dialogs.py`
- dpost runtime UI adapters boundary:
- `src/dpost/infrastructure/runtime_adapters/ui_adapters.py`
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
- `src/dpost/infrastructure/runtime_adapters/config_dependencies.py` (retired)
- Processing orchestration:
- `src/dpost/application/processing/file_process_manager.py`
- dpost processing helper module set:
- `src/dpost/application/processing/`
- dpost processing domain/application helper split:
- `src/dpost/domain/processing/batch_models.py`
- `src/dpost/domain/processing/staging.py`
- `src/dpost/domain/processing/text.py`
- `src/dpost/domain/naming/prefix_policy.py`
- `src/dpost/domain/naming/identifiers.py`
- `src/dpost/application/naming/policy.py`
- `src/dpost/infrastructure/storage/staging_dirs.py`
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
- `_invoke_rename_flow()` now uses iterative retry evaluation for non-ACCEPT
  rename loops, and transitional `_route_with_prefix()` helper indirection has
  been retired from canonical paths.
- `_rename_retry_policy_stage()` now defines non-ACCEPT retry warning/context
  policy for the rename loop.
- Plugin loading and registration:
- `src/dpost/plugins/system.py`
- Canonical reference plugin packages for runtime validation:
- `src/dpost/device_plugins/test_device/`
- `src/dpost/pc_plugins/test_pc/`
- Canonical concrete plugin package:
- `src/dpost/device_plugins/utm_zwick/`
- `src/dpost/device_plugins/extr_haake/`
- `src/dpost/device_plugins/erm_hioki/`
- `src/dpost/device_plugins/sem_phenomxl2/`
- `src/dpost/device_plugins/rmx_eirich_el1/`
- `src/dpost/device_plugins/rmx_eirich_r01/`
- `src/dpost/device_plugins/dsv_horiba/`
- `src/dpost/device_plugins/rhe_kinexus/`
- `src/dpost/device_plugins/psa_horiba/`
- Canonical concrete PC plugin package:
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
- Local record domain entity + persistence manager:
- `src/dpost/domain/records/local_record.py`
- `src/dpost/application/records/record_manager.py`
- Current Kadi backend implementation:
- `src/dpost/infrastructure/sync/kadi_manager.py`

## Current Test Isolation Baseline
- Pytest markers and suites enforce split test intent:
- `legacy` marker reserved for archived compatibility characterization suites.
- Canonical behavior and boundary coverage lives in:
  - `tests/unit/`
  - `tests/integration/`
  - `tests/manual/`
- Contract assertions formerly housed in transitional suites are now maintained
  in canonical test modules co-located with runtime, processing, plugin, and
  architecture ownership code paths.

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
- Processing value models, routing policy, staged batch models, staging
  reconstruction policy, and `LocalRecord` are now domain-owned under
  `src/dpost/domain/`; application paths retain orchestration and mutation
  helpers.
- Filename-prefix validation/sanitization and parse/identifier composition
  policy are now domain-owned under `src/dpost/domain/naming/`, with
  config-aware application facade usage in
  `src/dpost/application/naming/policy.py`; infrastructure storage no longer
  owns prefix or identifier policy functions.
- Stage-directory creation helper ownership now lives under infrastructure
  storage (`src/dpost/infrastructure/storage/staging_dirs.py`); application
  staging helper module has been retired.
- Domain ownership paths now avoid direct `dpost.application` and
  `dpost.infrastructure` imports for type/logging concerns.
- Transition runtime dependency shims have been retired from canonical dpost
  paths (`runtime_dependencies.py`, `config_dependencies.py`).
- dpost plugin profile support remains reference-first for kernel validation.
- dpost plugin loading now uses dpost-owned plugin protocol contracts;
  canonical plugin discovery groups now use `dpost.device_plugins` and
  `dpost.pc_plugins` with no legacy namespace fallback mappings in canonical
  dpost paths.
- Canonical reference profile plugins (`test_device`, `test_pc`) now load from
  dpost plugin namespaces with no legacy fallback path.
- Concrete UTM Zwick plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.utm_zwick`) with no legacy fallback path.
- Concrete EXTR HAAKE plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.extr_haake`) with no legacy fallback path.
- Concrete ERM HIOKI plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.erm_hioki`) with no legacy fallback path.
- Concrete SEM PHENOM XL2 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.sem_phenomxl2`) with no legacy fallback path.
- Concrete RMX EIRICH EL1 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rmx_eirich_el1`) with no legacy fallback path.
- Concrete RMX EIRICH R01 plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rmx_eirich_r01`) with no legacy fallback path.
- Concrete DSV HORIBA plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.dsv_horiba`) with no legacy fallback path.
- Concrete RHE KINEXUS plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.rhe_kinexus`) with no legacy fallback path.
- Concrete PSA HORIBA plugin now loads from canonical dpost namespace
  (`dpost.device_plugins.psa_horiba`) with no legacy fallback path.
- Concrete Zwick BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.zwick_blb`) with no legacy fallback path.
- Concrete HAAKE BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.haake_blb`) with no legacy fallback path.
- Concrete HIOKI BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.hioki_blb`) with no legacy fallback path.
- Concrete TISCHREM BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.tischrem_blb`) with no legacy fallback path.
- Concrete EIRICH BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.eirich_blb`) with no legacy fallback path.
- Concrete HORIBA BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.horiba_blb`) with no legacy fallback path.
- Concrete KINEXUS BLB PC plugin now loads from canonical dpost namespace
  (`dpost.pc_plugins.kinexus_blb`) with no legacy fallback path.
- dpost plugin loading now uses canonical hook namespace marker `dpost` and
  no longer orchestrates legacy hook namespaces in canonical dpost paths.
- Canonical extension contracts are now explicitly documented in
  `docs/architecture/extension-contracts.md`; `DevicePlugin` contract
  expectations include both configuration access and file-processor access.
- Legacy source package `src/ipat_watchdog/` is retired from the repository.
- Rename retries now evaluate directly through `_route_decision_stage()` within
  `_invoke_rename_flow()`; legacy `_route_with_prefix()` helper indirection is
  retired from canonical runtime code.
- `add_item_to_record()` now delegates record-context resolution, processor
  selection, invocation, datatype assignment, output finalization, and
  post-persist side effects; stage-call ordering remains coupled there and is
  an active decomposition target.

## Runtime Notes
- Headless-first runtime is the current execution posture.
- Framework-first sequencing is active: kernel and contracts are prioritized before concrete integrations.
- Sync is being moved toward optional adapter architecture for multi-ELN/database support.
- Default `dpost` install path no longer requires `kadi_apy`; Kadi is enabled via
  the `kadi` optional dependency group.
- Major structural updates should be tracked via ADRs in `docs/architecture/adr/`.
- Naming-settings single-source consolidation direction is tracked in:
  `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`.
