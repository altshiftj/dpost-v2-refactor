# Phase 10-13 Runtime Boundary Progress Report

## Date
- 2026-02-21

## Scope
- Continue Phase 9-13 autonomous execution after initial runtime-boundary
  extraction.
- Execute tests-first slices for deeper legacy-runtime retirement while keeping
  migration/full gates green.

## Gate Recovery Baseline
- Initial blocker: migration/full-suite failures in
  `tests/migration/test_plugin_discovery_hardening.py` from stale plugin
  directories:
  - `src/ipat_watchdog/device_plugins/pca_granupack`
  - `src/ipat_watchdog/pc_plugins/granupack_blb`
- Recovery action:
  removed both stale directories.
- Recovery verification:
  - `python -m pytest tests/migration/test_plugin_discovery_hardening.py`
    -> `6 passed`

## Phase 10 Increment: Application Orchestration Extraction
- Tests-first contract:
  - `tests/migration/test_phase10_application_orchestration_extraction.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_application_orchestration_extraction.py`
    -> `3 failed`
- Implementation:
  - added `src/dpost/application/services/runtime_startup.py`
  - added `src/dpost/application/services/__init__.py`
  - rewired `src/dpost/runtime/composition.py` to delegate runtime startup
    orchestration through `compose_runtime_context()`
- Green-state verification:
  - `python -m pytest tests/migration/test_phase10_application_orchestration_extraction.py`
    -> `3 passed`

## Phase 11 Increment: Runtime Infrastructure Boundary Extraction
- Tests-first contract:
  - `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py`
    -> `3 failed`
- Implementation:
  - added `src/dpost/infrastructure/runtime/ui_factory.py`
  - updated `src/dpost/infrastructure/runtime/__init__.py`
  - rewired `src/dpost/runtime/composition.py` to resolve UI factories through
    infrastructure adapter instead of direct legacy Tk import
- Green-state verification:
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py`
    -> `3 passed`

## Phase 12 Increment: Plugin/Config Boundary Migration
- Tests-first contract:
  - `tests/migration/test_phase12_plugin_config_boundary_migration.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_config_boundary_migration.py`
    -> `3 failed`
- Implementation:
  - added `src/dpost/runtime/startup_config.py`
  - added `src/dpost/plugins/profile_selection.py`
  - rewired `src/dpost/runtime/composition.py` to delegate plugin-profile and
    startup-config resolution to dedicated boundary modules
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_config_boundary_migration.py`
    -> `3 passed`

## Phase 13 Increment: Canonical Startup Direct-Import Retirement
- Tests-first contract:
  - `tests/migration/test_phase13_legacy_runtime_retirement.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py`
    -> `2 failed`
- Implementation:
  - added `src/dpost/infrastructure/logging.py` boundary and rewired
    `src/dpost/__main__.py` to use dpost logging import path
- Green-state verification:
  - `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py`
    -> `2 passed`

## Phase 13 Increment: Native Bootstrap Service Retirement
- Tests-first contract:
  - `tests/migration/test_phase13_native_bootstrap_service_retirement.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase13_native_bootstrap_service_retirement.py`
    -> `2 failed`
- Implementation:
  - replaced canonical bootstrap delegation with native dpost runtime bootstrap
    implementation in `src/dpost/runtime/bootstrap.py`
  - retired transition module
    `src/dpost/infrastructure/runtime/legacy_bootstrap_adapter.py`
  - added `src/dpost/infrastructure/runtime/bootstrap_dependencies.py` for
    infrastructure-owned dependency wiring
- Green-state verification:
  - `python -m pytest tests/migration/test_phase13_native_bootstrap_service_retirement.py`
    -> `2 passed`

## Phase 12 Increment: Plugin Loading Ownership Migration
- Tests-first contract:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `3 failed`
- Implementation:
  - added `src/dpost/plugins/system.py`
  - added `src/dpost/plugins/loading.py`
  - rewired runtime/bootstrap dependency wiring to use dpost plugin loading
    boundary
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `3 passed`

## Phase 10 Increment: Runtime App Rehost
- Tests-first contract:
  - `tests/migration/test_phase10_runtime_app_rehost.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `2 failed`
- Implementation:
  - added `src/dpost/application/runtime/device_watchdog_app.py`
  - added `src/dpost/application/runtime/__init__.py`
  - rewired runtime bootstrap dependencies to construct
    `dpost.application.runtime.DeviceWatchdogApp`
- Green-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `2 passed`

## Phase 11/13 Hardening Increment: dpost-Owned UI/Plugin/Observability Contracts
- Tests-first contracts tightened:
  - `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
  - `tests/migration/test_phase13_legacy_runtime_retirement.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py`
    -> `1 failed`
- Implementation:
  - added `src/dpost/plugins/contracts.py` and rewired plugin loading/system
    typing imports to dpost-owned protocol contracts
  - added `src/dpost/infrastructure/observability.py` and rewired
    `src/dpost/runtime/bootstrap.py` to avoid direct legacy observability
    import
  - replaced `src/dpost/infrastructure/logging.py` with dpost-owned logger
    implementation
  - added `src/dpost/application/ports/ui.py` and rewired
    `src/dpost/infrastructure/runtime/headless_ui.py` and
    `src/dpost/application/runtime/device_watchdog_app.py` typing imports to
    dpost-owned UI contract types
- Green-state verification:
  - `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `7 passed`
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_phase10_runtime_app_rehost.py`
    -> `6 passed`

## Phase 10/11 Hardening Increment: Runtime Dependency Boundary Isolation
- Tests-first contracts tightened:
  - `tests/migration/test_phase10_runtime_app_rehost.py`
  - `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py tests/migration/test_phase11_runtime_infrastructure_boundary.py`
    -> `2 failed`
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py`
    -> `1 failed`
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `1 failed`
- Implementation:
  - added `src/dpost/application/ports/interactions.py`
  - added `src/dpost/infrastructure/runtime/ui_adapters.py`
  - added `src/dpost/infrastructure/runtime/desktop_ui.py`
  - added `src/dpost/infrastructure/runtime/config_dependencies.py`
  - added `src/dpost/application/runtime/runtime_dependencies.py`
  - added `src/dpost/application/interactions/messages.py`
  - rewired canonical runtime app/bootstrap infrastructure modules to consume
    these dpost-owned boundaries instead of direct legacy imports
  - rewired default sync manager construction in
    `src/dpost/infrastructure/runtime/bootstrap_dependencies.py` through
    `KadiSyncAdapter` boundary
- Green-state verification:
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_phase10_runtime_app_rehost.py tests/migration/test_sync_adapter_selection.py`
    -> `28 passed`
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py`
    -> `21 passed`

## Deep-Core Increment: Processing Helper Ownership + Native Storage Boundary
- Tests-first contract tightening:
  - `tests/migration/test_phase10_runtime_app_rehost.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `2 failed`
- Implementation:
  - added dpost-owned processing helper modules under
    `src/dpost/application/processing/`:
    - `device_resolver.py`
    - `error_handling.py`
    - `file_processor_abstract.py`
    - `modified_event_gate.py`
    - `processor_factory.py`
    - `record_flow.py`
    - `record_utils.py`
    - `rename_flow.py`
    - `routing.py`
    - `stability_tracker.py`
  - rewired `src/dpost/application/processing/file_process_manager.py` to
    consume dpost processing helper modules and removed direct
    `ipat_watchdog.core.processing.*` imports
  - rehosted `src/dpost/infrastructure/storage/filesystem_utils.py` to a
    native dpost implementation path with dpost boundary imports
  - expanded `src/dpost/application/config/__init__.py` exports to include
    `StabilityOverride` required by dpost processing stability typing paths
- Green-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `20 passed`
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_sync_adapter_selection.py tests/migration/test_phase13_legacy_runtime_retirement.py`
    -> `53 passed`

## Deep-Core Increment: Native Config + Metrics Boundary Ownership
- Tests-first contract tightening:
  - `tests/migration/test_phase10_runtime_app_rehost.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py`
    -> `2 failed`
- Implementation:
  - added native dpost config internals under `src/dpost/application/config/`:
    - `schema.py`
    - `service.py`
    - `runtime.py`
    - updated `__init__.py` exports to dpost-owned modules
  - added native dpost metrics ownership under
    `src/dpost/application/metrics.py`
  - implemented registry-safe metric collector reuse in dpost metrics boundary
    to avoid duplicate Prometheus collector registration during mixed legacy +
    migration test runs
  - tightened `AGENTS.md` temporary legacy import allowlist to remove
    config/metrics/storage exceptions now that these boundaries are dpost-owned
- Green-state verification:
  - `python -m pytest tests/migration/test_configuration_consolidation.py tests/migration/test_phase10_runtime_app_rehost.py`
    -> `27 passed`
  - `python -m pytest tests/migration/test_naming_constants_consolidation.py tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_sync_adapter_selection.py tests/migration/test_phase13_legacy_runtime_retirement.py tests/integration/test_settings_integration.py tests/unit/core/settings/test_settings_manager.py tests/unit/core/processing/test_file_process_manager.py tests/unit/core/session/test_session_manager.py`
    -> `73 passed`

## Deep-Core Increment: Shim Retirement + Desktop UI Rehost + Plugin Group Canonicalization
- Tests-first contracts tightened:
  - `tests/migration/test_phase11_runtime_infrastructure_boundary.py`
  - `tests/migration/test_runtime_mode_selection.py`
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 errors` (missing `dpost.infrastructure.runtime.tkinter_ui`)
- Implementation:
  - added dpost-owned desktop UI implementation modules:
    - `src/dpost/infrastructure/runtime/tkinter_ui.py`
    - `src/dpost/infrastructure/runtime/dialogs.py`
  - rewired `src/dpost/infrastructure/runtime/desktop_ui.py` to resolve
    `TKinterRuntimeUI` from dpost-owned runtime infrastructure module.
  - updated runtime mode and infrastructure migration tests to use dpost-owned
    desktop UI contracts.
  - added canonical plugin namespace packages:
    - `src/dpost/device_plugins/__init__.py`
    - `src/dpost/pc_plugins/__init__.py`
  - added `src/dpost/plugins/legacy_compat.py` to isolate temporary legacy
    plugin namespace fallback mapping.
  - rewired `src/dpost/plugins/system.py` to use canonical dpost entrypoint
    groups (`dpost.device_plugins`, `dpost.pc_plugins`) while preserving
    compatibility fallback via `legacy_compat`.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `26 passed`
  - `python -m pytest -m migration`
    -> `136 passed, 302 deselected`

## Deep-Core Increment: Plugin Hook Namespace Canonicalization
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - rewired `src/dpost/plugins/system.py` to set canonical plugin hook
    namespace marker to `dpost` while preserving legacy marker compatibility
    through isolated dual-plugin-manager orchestration.
  - updated `src/dpost/plugins/legacy_compat.py` with explicit
    `LEGACY_PLUGIN_NAMESPACE`.
  - reduced source-level legacy literal spread by updating `src/dpost/__init__.py`
    and isolating `ipat_watchdog` literals to
    `src/dpost/plugins/legacy_compat.py`.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `6 passed`
  - `python -m pytest tests/migration/test_phase11_runtime_infrastructure_boundary.py tests/migration/test_runtime_mode_selection.py tests/migration/test_reference_plugin_flow.py tests/migration/test_sync_adapter_selection.py`
    -> `31 passed`

## Deep-Core Increment: Reference Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `1 failed`
- Implementation:
  - added canonical dpost reference plugin packages:
    - `src/dpost/device_plugins/test_device/`
    - `src/dpost/pc_plugins/test_pc/`
  - added dpost-owned reference plugin modules/settings/processor:
    - `src/dpost/device_plugins/test_device/plugin.py`
    - `src/dpost/device_plugins/test_device/settings.py`
    - `src/dpost/device_plugins/test_device/file_processor.py`
    - `src/dpost/pc_plugins/test_pc/plugin.py`
    - `src/dpost/pc_plugins/test_pc/settings.py`
  - retained legacy fallback compatibility while preferring canonical dpost
    reference plugin modules.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `7 passed`
  - `python -m pytest tests/migration/test_phase12_plugin_config_boundary_migration.py tests/migration/test_reference_plugin_flow.py tests/migration/test_runtime_mode_selection.py tests/migration/test_sync_adapter_selection.py`
    -> `21 passed`

## Deep-Core Increment: Concrete UTM Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `1 failed`
- Implementation:
  - added canonical dpost UTM plugin package:
    - `src/dpost/device_plugins/utm_zwick/`
  - added dpost-owned UTM plugin modules:
    - `src/dpost/device_plugins/utm_zwick/plugin.py`
    - `src/dpost/device_plugins/utm_zwick/settings.py`
    - `src/dpost/device_plugins/utm_zwick/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.utm_zwick` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `8 passed`
  - `python -m pytest tests/unit/device_plugins/utm_zwick/test_file_processor.py tests/integration/test_utm_zwick_integration.py`
    -> `9 passed`

## Deep-Core Increment: Concrete Zwick BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `1 failed`
- Implementation:
  - added canonical dpost Zwick BLB PC plugin package:
    - `src/dpost/pc_plugins/zwick_blb/`
  - added dpost-owned Zwick BLB modules:
    - `src/dpost/pc_plugins/zwick_blb/plugin.py`
    - `src/dpost/pc_plugins/zwick_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.zwick_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `9 passed`
  - `python -m pytest tests/unit/pc_plugins/test_pc_plugins.py tests/unit/plugin_system/test_plugin_loader.py`
    -> `12 passed`

## Deep-Core Increment: Concrete EXTR HAAKE Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost EXTR HAAKE plugin package:
    - `src/dpost/device_plugins/extr_haake/`
  - added dpost-owned EXTR HAAKE modules:
    - `src/dpost/device_plugins/extr_haake/plugin.py`
    - `src/dpost/device_plugins/extr_haake/settings.py`
    - `src/dpost/device_plugins/extr_haake/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.extr_haake` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `11 passed`

## Deep-Core Increment: Concrete HAAKE BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost HAAKE BLB PC plugin package:
    - `src/dpost/pc_plugins/haake_blb/`
  - added dpost-owned HAAKE BLB PC modules:
    - `src/dpost/pc_plugins/haake_blb/plugin.py`
    - `src/dpost/pc_plugins/haake_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.haake_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `11 passed`

## Deep-Core Increment: Concrete ERM HIOKI Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost ERM HIOKI plugin package:
    - `src/dpost/device_plugins/erm_hioki/`
  - added dpost-owned ERM HIOKI modules:
    - `src/dpost/device_plugins/erm_hioki/plugin.py`
    - `src/dpost/device_plugins/erm_hioki/settings.py`
    - `src/dpost/device_plugins/erm_hioki/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.erm_hioki` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `13 passed`

## Deep-Core Increment: Concrete HIOKI BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost HIOKI BLB PC plugin package:
    - `src/dpost/pc_plugins/hioki_blb/`
  - added dpost-owned HIOKI BLB PC modules:
    - `src/dpost/pc_plugins/hioki_blb/plugin.py`
    - `src/dpost/pc_plugins/hioki_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.hioki_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `13 passed`

## Deep-Core Increment: Concrete SEM PHENOM XL2 Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost SEM PHENOM XL2 plugin package:
    - `src/dpost/device_plugins/sem_phenomxl2/`
  - added dpost-owned SEM PHENOM XL2 modules:
    - `src/dpost/device_plugins/sem_phenomxl2/plugin.py`
    - `src/dpost/device_plugins/sem_phenomxl2/settings.py`
    - `src/dpost/device_plugins/sem_phenomxl2/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.sem_phenomxl2` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `15 passed`

## Deep-Core Increment: Concrete TISCHREM BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost TISCHREM BLB PC plugin package:
    - `src/dpost/pc_plugins/tischrem_blb/`
  - added dpost-owned TISCHREM BLB PC modules:
    - `src/dpost/pc_plugins/tischrem_blb/plugin.py`
    - `src/dpost/pc_plugins/tischrem_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.tischrem_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `15 passed`

## Deep-Core Increment: Concrete RMX EIRICH EL1 Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `3 failed`
- Implementation:
  - added canonical dpost RMX EIRICH EL1 plugin package:
    - `src/dpost/device_plugins/rmx_eirich_el1/`
  - added dpost-owned RMX EIRICH EL1 modules:
    - `src/dpost/device_plugins/rmx_eirich_el1/plugin.py`
    - `src/dpost/device_plugins/rmx_eirich_el1/settings.py`
    - `src/dpost/device_plugins/rmx_eirich_el1/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.rmx_eirich_el1` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `18 passed`

## Deep-Core Increment: Concrete RMX EIRICH R01 Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `3 failed`
- Implementation:
  - added canonical dpost RMX EIRICH R01 plugin package:
    - `src/dpost/device_plugins/rmx_eirich_r01/`
  - added dpost-owned RMX EIRICH R01 modules:
    - `src/dpost/device_plugins/rmx_eirich_r01/plugin.py`
    - `src/dpost/device_plugins/rmx_eirich_r01/settings.py`
    - `src/dpost/device_plugins/rmx_eirich_r01/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.rmx_eirich_r01` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `18 passed`

## Deep-Core Increment: Concrete EIRICH BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `3 failed`
- Implementation:
  - added canonical dpost EIRICH BLB PC plugin package:
    - `src/dpost/pc_plugins/eirich_blb/`
  - added dpost-owned EIRICH BLB PC modules:
    - `src/dpost/pc_plugins/eirich_blb/plugin.py`
    - `src/dpost/pc_plugins/eirich_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.eirich_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `18 passed`

## Deep-Core Increment: Concrete DSV HORIBA Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost DSV HORIBA plugin package:
    - `src/dpost/device_plugins/dsv_horiba/`
  - added dpost-owned DSV HORIBA modules:
    - `src/dpost/device_plugins/dsv_horiba/plugin.py`
    - `src/dpost/device_plugins/dsv_horiba/settings.py`
    - `src/dpost/device_plugins/dsv_horiba/file_processor.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.dsv_horiba` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `20 passed`

## Deep-Core Increment: Concrete HORIBA BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost HORIBA BLB PC plugin package:
    - `src/dpost/pc_plugins/horiba_blb/`
  - added dpost-owned HORIBA BLB PC modules:
    - `src/dpost/pc_plugins/horiba_blb/plugin.py`
    - `src/dpost/pc_plugins/horiba_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.horiba_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `20 passed`

## Deep-Core Increment: Concrete RHE KINEXUS Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost RHE KINEXUS plugin package:
    - `src/dpost/device_plugins/rhe_kinexus/`
  - added dpost-owned RHE KINEXUS modules:
    - `src/dpost/device_plugins/rhe_kinexus/plugin.py`
    - `src/dpost/device_plugins/rhe_kinexus/settings.py`
    - `src/dpost/device_plugins/rhe_kinexus/file_processor.py`
  - added dpost processing helper modules required by Kinexus staged
    preprocessing:
    - `src/dpost/application/processing/batch_models.py`
    - `src/dpost/application/processing/staging_utils.py`
    - `src/dpost/application/processing/text_utils.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.device_plugins.rhe_kinexus` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `22 passed`

## Deep-Core Increment: Concrete KINEXUS BLB PC Plugin Namespace Rehost
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - added canonical dpost KINEXUS BLB PC plugin package:
    - `src/dpost/pc_plugins/kinexus_blb/`
  - added dpost-owned KINEXUS BLB PC modules:
    - `src/dpost/pc_plugins/kinexus_blb/plugin.py`
    - `src/dpost/pc_plugins/kinexus_blb/settings.py`
  - preserved runtime behavior while resolving canonical plugin loading through
    `dpost.pc_plugins.kinexus_blb` before legacy fallback.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `22 passed`

## Deep-Core Increment: Concrete PSA HORIBA Plugin Namespace Rehost
- Migration contract:
  - extended `tests/migration/test_phase12_plugin_loading_ownership.py` with
    `test_concrete_psa_horiba_plugin_loads_from_dpost_namespace`.
- Implementation:
  - added canonical dpost PSA HORIBA plugin package:
    - `src/dpost/device_plugins/psa_horiba/`
  - added dpost-owned PSA HORIBA modules:
    - `src/dpost/device_plugins/psa_horiba/plugin.py`
    - `src/dpost/device_plugins/psa_horiba/settings.py`
    - `src/dpost/device_plugins/psa_horiba/file_processor.py`
  - preserved staged CSV/NGB pairing behavior while resolving canonical plugin
    loading through `dpost.device_plugins.psa_horiba` before legacy fallback.
- Verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `23 passed`

## Deep-Core Increment: Plugin Compatibility Seam Retirement
- Tests-first contracts tightened:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `2 failed`
- Implementation:
  - removed transition compatibility module:
    - deleted `src/dpost/plugins/legacy_compat.py`
  - rewired `src/dpost/plugins/system.py` to canonical-only dpost plugin
    manager behavior:
    - removed legacy hook namespace orchestration
    - removed legacy entrypoint-group and built-in package fallback loading
    - removed legacy module fallback candidates during lazy loading
  - updated governance/source-of-truth docs and AGENTS policy to retire
    temporary dpost legacy import exceptions.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py`
    -> `24 passed`

## Deep-Core Increment: Records/Sync Immediate-Error Parity Hardening
- Tests-first contract:
  - `tests/migration/test_phase13_records_sync_parity.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase13_records_sync_parity.py`
    -> `1 failed, 2 passed`
- Implementation:
  - added migration parity tests to lock:
    - immediate-sync trigger behavior when pending uploads remain
    - skip behavior when records are already fully uploaded
    - user-visible sync error surfacing when immediate sync fails
  - updated dpost interaction message catalog with sync failure messages:
    - `src/dpost/application/interactions/messages.py`
  - updated immediate-sync exception handling in
    `src/dpost/application/processing/file_process_manager.py` to surface
    actionable UI errors while preserving best-effort non-crashing sync
    behavior.
- Green-state verification:
  - `python -m pytest tests/migration/test_phase13_records_sync_parity.py`
    -> `3 passed`

## Deep-Core Increment: Transition Glue Retirement Hardening
- Tests-first contracts tightened:
  - `tests/migration/test_phase10_runtime_app_rehost.py`
  - `tests/migration/test_phase13_legacy_runtime_retirement.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase10_runtime_app_rehost.py::test_dpost_processing_pipeline_retired_prepare_request_transition_helper`
    -> `1 failed`
- Implementation:
  - removed transition-only helper from canonical dpost processing pipeline:
    - deleted `_ProcessingPipeline._prepare_request()` in
      `src/dpost/application/processing/file_process_manager.py`
  - added explicit migration assertion enforcing no legacy namespace literals in
    canonical dpost source tree:
    - `test_all_dpost_source_modules_have_no_legacy_namespace_literals` in
      `tests/migration/test_phase13_legacy_runtime_retirement.py`
- Green-state verification:
  - `python -m pytest tests/migration/test_phase13_legacy_runtime_retirement.py tests/migration/test_phase10_runtime_app_rehost.py::test_dpost_processing_pipeline_retired_prepare_request_transition_helper`
    -> `6 passed`

## Deep-Core Increment: Plugin Contract Boundary Finalization
- Tests-first contract:
  - `tests/migration/test_phase12_plugin_loading_ownership.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py::test_device_plugin_contract_requires_file_processor_accessor`
    -> `1 failed`
- Implementation:
  - tightened canonical plugin protocol contract in
    `src/dpost/plugins/contracts.py`:
    - `DevicePlugin` now requires `get_file_processor()` in addition to
      `get_config()`
- Green-state verification:
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py::test_device_plugin_contract_requires_file_processor_accessor`
    -> `1 passed`
  - `python -m pytest tests/migration/test_phase12_plugin_loading_ownership.py tests/migration/test_phase13_legacy_runtime_retirement.py tests/migration/test_phase13_records_sync_parity.py tests/migration/test_phase10_runtime_app_rehost.py`
    -> `56 passed`

## Deep-Core Increment: Extension Contract and Contributor Surface Hardening
- Architecture/governance implementation:
  - added canonical extension contract reference:
    - `docs/architecture/extension-contracts.md`
  - added ADR for canonical extension contracts and legacy namespace
    retirement:
    - `docs/architecture/adr/ADR-0003-canonical-extension-contracts-and-legacy-namespace-retirement.md`
  - updated architecture and contributor docs:
    - `docs/architecture/README.md`
    - `docs/architecture/architecture-contract.md`
    - `docs/architecture/architecture-baseline.md`
    - `docs/architecture/responsibility-catalog.md`
    - `DEVELOPER_README.md`
    - `docs/reports/20260221-full-legacy-decoupling-functional-architecture-audit.md`
    - `docs/checklists/20260221-dpost-full-legacy-decoupling-clean-architecture-checklist.md`

## Full Legacy Repo Retirement Kickoff: Shared Harness Helper Decoupling
- Tests-first contract:
  - `tests/migration/test_full_legacy_repo_retirement_harness.py`
- Red-state verification:
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py`
    -> `2 failed`, then `1 failed, 2 passed`, then `1 failed, 3 passed`, then
    `1 failed, 4 passed`, then `1 failed, 5 passed`, then `1 failed, 6 passed`,
    then `1 failed, 7 passed`, then `1 failed, 8 passed`, then
    `1 failed, 9 passed`
- Implementation:
  - migrated shared helper boundaries away from direct legacy interaction/sync
    imports:
    - `tests/helpers/fake_ui.py`
    - `tests/helpers/fake_sync.py`
  - added process-manager helper retirement guard and migrated helper away from
    legacy processing model imports:
    - `tests/helpers/fake_process_manager.py`
  - added fake-processor helper retirement guard and migrated helper away from
    legacy processing abstract imports:
    - `tests/helpers/fake_processor.py`
  - added legacy-metrics retirement guard and migrated legacy metrics module to
    re-export canonical dpost metrics:
    - `src/ipat_watchdog/metrics.py`
  - removed hardcoded legacy observer monkeypatch literal in conftest by
    deriving target module dynamically from `DeviceWatchdogApp.__module__`:
    - `tests/conftest.py`
  - migrated shared watchdog fixture and unit app test imports to canonical
  dpost runtime app ownership:
    - `tests/conftest.py`
    - `tests/unit/core/app/test_device_watchdog_app.py`
  - migrated integration runtime app imports and observer patch targets to
    canonical dpost runtime module ownership:
    - `tests/integration/test_integration.py`
    - `tests/integration/test_multi_processor_app_flow.py`
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
  - preserved integration behavior parity by explicitly wiring legacy
    `FileProcessManager` into migrated runtime app fixtures where required:
    - `tests/integration/test_device_integrations.py`
    - `tests/integration/test_extr_haake_safesave.py`
  - migrated observability unit tests to canonical dpost infrastructure module:
    - `tests/unit/test_observability.py`
  - migrated loader/plugin unit tests to canonical dpost plugin loading
    boundaries:
    - `tests/unit/loader/test_pc_device_mapping.py`
    - `tests/unit/plugins/test_test_plugins_integration.py`
- Green-state verification:
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py`
    -> `10 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py`
    -> `8 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/test_observability.py`
    -> `15 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/unit/loader/test_pc_device_mapping.py tests/unit/plugins/test_test_plugins_integration.py`
    -> `31 passed`
  - `python -m pytest tests/migration/test_full_legacy_repo_retirement_harness.py tests/integration/test_integration.py tests/integration/test_device_integrations.py tests/integration/test_multi_processor_app_flow.py tests/integration/test_extr_haake_safesave.py`
    -> `29 passed`
  - `@' ... import dpost runtime then ipat runtime ... '@ | python -`
    -> `ok`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/unit/core/processing/test_file_process_manager.py tests/migration/test_processing_pipeline_stage_boundaries.py tests/integration/test_multi_processor_app_flow.py`
    -> `55 passed`
  - `python -m pytest tests/unit/core/app/test_device_watchdog_app.py tests/integration/test_integration.py tests/integration/test_device_integrations.py`
    -> `26 passed`

## Global Gate Verification (Final)
- `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 passed`
- `python -m pytest -m migration`
  -> `171 passed, 302 deselected`
- `python -m ruff check .`
  -> `All checks passed!`
- `python -m black --check .`
  -> `157 files would be left unchanged.`
- `python -m pytest`
  -> `472 passed, 1 skipped`

## Notes
- During this run, `python -m black --check .` initially failed on 4 files,
  and later on 9 files, 5 files, 1 file, 7 files, 1 file, 4 files, and 3 files
  after additional runtime-boundary implementation.
  Formatting was applied with `python -m black ...`, and all required gates
  were re-run to final green.
- Current concrete-plugin rehost slice completed with Black check green on
  first pass (`110 files would be left unchanged`).
- Hioki concrete-plugin slice required one formatter pass on
  `src/dpost/device_plugins/erm_hioki/file_processor.py` before
  `python -m black --check .` returned
  `117 files would be left unchanged`.
- SEM concrete-plugin slice required formatter passes on
  `src/dpost/device_plugins/sem_phenomxl2/settings.py` and
  `src/dpost/device_plugins/sem_phenomxl2/file_processor.py` before
  `python -m black --check .` returned
  `124 files would be left unchanged`.
- Eirich concrete-plugin slice required formatter passes on
  `src/dpost/device_plugins/rmx_eirich_el1/file_processor.py` and
  `src/dpost/device_plugins/rmx_eirich_r01/file_processor.py` before
  `python -m black --check .` returned
  `135 files would be left unchanged`.
- DSV concrete-plugin slice required one formatter pass on
  `src/dpost/device_plugins/dsv_horiba/file_processor.py` before
  `python -m black --check .` returned
  `142 files would be left unchanged`.
- Conftest full import migration remains staged after exploratory attempts
  exposed runtime/config/storage coupling in legacy tests; the migration
  proceeds in bounded slices with metrics ownership now unified first.
- Latest checkpoint required one formatter pass on
  `tests/migration/test_full_legacy_repo_retirement_harness.py` before
  `python -m black --check .` returned
  `157 files would be left unchanged`.
- Kinexus concrete-plugin slice required one formatter pass on
  `src/dpost/device_plugins/rhe_kinexus/file_processor.py` before
  `python -m black --check .` returned
  `152 files would be left unchanged`.
- PSA concrete-plugin slice completed with Black check green on first pass
  (`156 files would be left unchanged`).
- Compatibility-seam retirement slice required formatter passes on
  `src/dpost/plugins/system.py` and
  `tests/migration/test_phase12_plugin_loading_ownership.py` before
  `python -m black --check .` returned
  `155 files would be left unchanged`.
- Records/sync parity hardening slice completed with Black check green on first
  pass (`156 files would be left unchanged`).

## Remaining Risk / Open Work
- In-repo concrete plugin package rehosting is now complete across
  `src/dpost/device_plugins/` and `src/dpost/pc_plugins/`.
- Canonical dpost plugin loading paths now run without legacy namespace or
  legacy hook compatibility seams (`src/dpost/plugins/legacy_compat.py`
  retired; `src/dpost/plugins/system.py` canonical-only).
- Remaining migration risk is focused on deprecating and eventually retiring
  legacy package trees under `src/ipat_watchdog/device_plugins/` and
  `src/ipat_watchdog/pc_plugins/` while preserving contributor migration
  guidance.
