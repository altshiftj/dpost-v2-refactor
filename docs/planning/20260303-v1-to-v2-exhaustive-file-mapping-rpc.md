# RPC: V1 to V2 Exhaustive File Mapping (Parallel-Ready)

## Date
- 2026-03-03

## Status
- Draft for Review

## Purpose
- Define an exhaustive, file-level migration map from `src/dpost` (V1) to `src/dpost_v2` (V2) before writing implementation code.
- Make the plan model-parallel ready: each model works in disjoint lanes with explicit stitching contracts.

## Scope and Assumptions
- Scope: every Python script currently under `src/dpost/**/*.py`.
- Total scripts mapped: 157
- This is a planning map; no behavior-changing implementation is included in this artifact.

## Target V2 Topology (Planned)
```text
src/dpost_v2/
  __main__.py
  runtime/
  application/
    contracts/
    startup/
    ingestion/
    records/
    runtime/
    session/
    naming/
  domain/
    naming/
    routing/
    processing/
    records/
  infrastructure/
    runtime/ui/
    storage/
    sync/
    observability/
  plugins/
    contracts.py
    host.py
    discovery.py
    catalog.py
    profile_selection.py
    devices/
    pcs/
```

## Planned V2 File and Folder Structure (Implementation Target)
```text
src/dpost_v2/
  __init__.py
  __main__.py
  runtime/{composition.py,startup_dependencies.py}
  application/contracts/{context.py,ports.py,events.py,plugin_contracts.py}
  application/startup/{settings.py,settings_schema.py,settings_service.py,bootstrap.py,context.py}
  application/runtime/{dpost_app.py}
  application/session/{session_manager.py}
  application/records/{service.py}
  application/ingestion/{engine.py,runtime_services.py,processor_factory.py}
  application/ingestion/models/{candidate.py}
  application/ingestion/stages/{pipeline.py,resolve.py,stabilize.py,route.py,persist.py,post_persist.py}
  application/ingestion/policies/{retry_planner.py,force_path.py,failure_outcome.py,failure_emitter.py,immediate_sync_error_emitter.py,modified_event_gate.py,error_handling.py}
  domain/naming/{identifiers.py,prefix_policy.py,policy.py}
  domain/routing/{rules.py}
  domain/processing/{models.py,batch_models.py,text.py,staging.py}
  domain/records/{local_record.py}
  infrastructure/storage/{record_store.py,file_ops.py,staging_dirs.py}
  infrastructure/sync/{noop.py,kadi.py}
  infrastructure/runtime/ui/{factory.py,adapters.py,headless.py,tkinter.py,desktop.py,dialogs.py}
  infrastructure/observability/{logging.py,metrics.py,tracing.py}
  plugins/{host.py,discovery.py,catalog.py,profile_selection.py,contracts.py}
  plugins/devices/<device>/{plugin.py,settings.py,processor.py}
  plugins/pcs/<pc>/{plugin.py,settings.py}
```

## Planned V2 File Content (Non-`__init__.py`)
| File | Planned Content |
|---|---|
| `src/dpost_v2/__main__.py` | Parse mode/profile args and dispatch runtime entrypoint (`v1`,`v2`,`shadow`). |
| `src/dpost_v2/runtime/composition.py` | Build dependency graph, wire ports to adapters, return app runtime object. |
| `src/dpost_v2/runtime/startup_dependencies.py` | Resolve startup dependencies from env/config files and runtime mode. |
| `application/contracts/context.py` | Immutable `RuntimeContext`, `ProcessingContext`, context constructors/validators. |
| `application/contracts/ports.py` | Protocol interfaces for UI, storage, sync, events, plugin host, clock, filesystem. |
| `application/contracts/events.py` | Event/message dataclasses and enums shared across lanes. |
| `application/contracts/plugin_contracts.py` | Plugin capability protocols, processor abstract types, plugin metadata types. |
| `application/startup/settings.py` | Startup settings model and normalization helpers. |
| `application/startup/settings_schema.py` | Typed schema declarations including NamingSettings and validation rules. |
| `application/startup/settings_service.py` | Load/merge settings sources and expose validated settings object. |
| `application/startup/bootstrap.py` | Startup orchestration sequence: load settings, build composition, launch runtime. |
| `application/startup/context.py` | Explicit context builder replacing ambient `current()/get_service()` access. |
| `application/runtime/dpost_app.py` | Top-level orchestration loop for observer events -> ingestion engine -> outcomes. |
| `application/session/session_manager.py` | Session timeout, state transitions, and lifecycle hooks. |
| `application/records/service.py` | Record lifecycle API (`create`, `update`, `mark_unsynced`, `save`) via record port. |
| `application/ingestion/engine.py` | Stage runner coordinating resolve/stabilize/route/persist/post-persist stages. |
| `application/ingestion/runtime_services.py` | Side-effect facade consumed by stage machine (fs/io/sync/ui/event ports). |
| `application/ingestion/processor_factory.py` | Select and instantiate processor from plugin registry + context. |
| `application/ingestion/models/candidate.py` | Candidate artifact metadata model and helper constructors. |
| `application/ingestion/stages/pipeline.py` | Pure stage sequencing logic and stage transition rules. |
| `application/ingestion/stages/resolve.py` | Resolve device/plugin and create candidate metadata. |
| `application/ingestion/stages/stabilize.py` | Stability gate logic and settle-time policy application. |
| `application/ingestion/stages/route.py` | Route decision orchestration using domain routing + naming policy. |
| `application/ingestion/stages/persist.py` | Persist/rename/reject flows and record update integration. |
| `application/ingestion/stages/post_persist.py` | Post-persist bookkeeping, immediate sync trigger, emission hooks. |
| `application/ingestion/policies/retry_planner.py` | Shared retry delay calculation and retry-limit rules. |
| `application/ingestion/policies/force_path.py` | Force-path override policy and guard checks. |
| `application/ingestion/policies/failure_outcome.py` | Failure outcome model and normalization rules. |
| `application/ingestion/policies/failure_emitter.py` | Failure event emission adapter hooks. |
| `application/ingestion/policies/immediate_sync_error_emitter.py` | Emit immediate-sync failure outcomes consistently. |
| `application/ingestion/policies/modified_event_gate.py` | Debounce policy to suppress duplicate modified events. |
| `application/ingestion/policies/error_handling.py` | Exception-to-outcome mapping and severity classification. |
| `domain/naming/identifiers.py` | Parse/format artifact identifiers and separator-aware tokenization. |
| `domain/naming/prefix_policy.py` | Prefix derivation rules independent of infrastructure concerns. |
| `domain/naming/policy.py` | Canonical naming composition (pattern + separator + explicit shape). |
| `domain/routing/rules.py` | Pure routing rules and deterministic path decision functions. |
| `domain/processing/models.py` | Processing domain types and outcome models. |
| `domain/processing/batch_models.py` | Batch outcome/data models for grouped processing operations. |
| `domain/processing/text.py` | Text parsing/normalization helpers used by processors. |
| `domain/processing/staging.py` | Staging-domain invariants and transitions. |
| `domain/records/local_record.py` | Local record entity contract and invariants. |
| `infrastructure/storage/record_store.py` | Transactional record repository adapter (SQLite) implementing RecordStorePort. |
| `infrastructure/storage/file_ops.py` | Concrete file operations with explicit context input only. |
| `infrastructure/storage/staging_dirs.py` | Staging directory derivation and filesystem path policies. |
| `infrastructure/sync/noop.py` | No-op sync backend for offline/testing mode. |
| `infrastructure/sync/kadi.py` | Kadi sync adapter implementing SyncPort with structured outcomes. |
| `infrastructure/runtime/ui/factory.py` | Select UI adapter implementation for headless/desktop mode. |
| `infrastructure/runtime/ui/adapters.py` | UI adapter shims implementing application UI port. |
| `infrastructure/runtime/ui/headless.py` | Headless UI adapter for CI/automation. |
| `infrastructure/runtime/ui/tkinter.py` | Tkinter UI implementation for desktop mode. |
| `infrastructure/runtime/ui/desktop.py` | Desktop UI orchestration and shared desktop view model wiring. |
| `infrastructure/runtime/ui/dialogs.py` | Dialog helpers and user-prompt composition. |
| `infrastructure/observability/logging.py` | Logger config, structured log formatter, sink setup. |
| `infrastructure/observability/metrics.py` | Metrics emitters/counters/timers aligned with stage outcomes. |
| `infrastructure/observability/tracing.py` | Trace/event emission with correlation IDs across stages. |
| `plugins/host.py` | Plugin runtime host, capability lookup, and lifecycle control. |
| `plugins/discovery.py` | Plugin discovery/registration from modules/manifests. |
| `plugins/catalog.py` | Plugin metadata catalog and lookup APIs. |
| `plugins/profile_selection.py` | Profile-to-enabled-plugin resolution policy. |
| `plugins/contracts.py` | Plugin-facing contract aliases/re-exports for adapter packages. |
| `plugins/devices/<device>/settings.py` | Device-specific typed settings and defaults. |
| `plugins/devices/<device>/plugin.py` | Device plugin adapter exposing capability and processor factory hooks. |
| `plugins/devices/<device>/processor.py` | Device-specific parsing, preprocessing, and candidate derivation logic. |
| `plugins/pcs/<pc>/settings.py` | PC plugin typed settings and upload/sync config defaults. |
| `plugins/pcs/<pc>/plugin.py` | PC plugin adapter for PC-side integration behavior. |

## Mapping Semantics
- `Migrate`: same responsibility, moved with minimal structural change.
- `Move`/`Rename`: responsibility unchanged, path/name clarified for V2 boundaries.
- `Merge`: several V1 modules become one V2 module with a single owner.
- `Split`: one V1 module is decomposed into explicit V2 modules/stages.
- `Retire/Replace`: V1 seam removed; behavior handled by explicit V2 contract/context.

## Transform Summary
- Merge: 18
- Migrate: 82
- Move: 30
- Rename: 18
- Retire/Replace: 1
- Rewrite: 2
- Split: 6

## Model-Parallel Lanes (Disjoint Ownership)
- `Startup-Core`: runtime bootstrap/composition/settings lifecycle.
- `Contracts-Core`: shared context/ports/contracts/events; no adapter logic.
- `Processing-Kernel`: ingestion engine, stage machine, policies, and orchestration splits.
- `Records-Core`: record lifecycle service and persistence-facing application semantics.
- `Domain-Core`: pure naming/routing/processing/record entities and policies.
- `Infra-Storage`: file operations and staging directory adapters.
- `Infra-Sync`: sync adapters (noop + kadi) behind SyncPort.
- `Infra-UI`: headless/desktop/tkinter runtime UI adapters.
- `Infra-Observability`: logging/metrics/tracing adapter boundary.
- `Plugin-Host`: plugin discovery, host lifecycle, registry/catalog, contracts.
- `Plugin-Device`: one lane per device plugin package family.
- `Plugin-PC`: one lane per PC plugin package family.

## Stitching Protocol (For Multi-Model Execution)
1. Freeze contracts first (`application/contracts`, `plugins/contracts`, `RuntimeContext`).
2. Merge order: `Contracts-Core` -> `Domain-Core` -> `Processing-Kernel/Records-Core` -> `Infrastructure` -> `Plugin-*` -> `Startup-Core`.
3. Every lane PR must include: changed files only in owned paths, updated mapping references if paths shift, and parity notes.
4. Cross-lane changes are blocked unless contract-owner approval is present and dependent lanes rebase to the new contract hash.
5. No lane may import from another lane's infrastructure implementation directly; only contract imports are allowed across lanes.

## Lane Load (Script Count)
- App-Core: 1
- Contracts-Core: 9
- Domain-Core: 14
- Infra-Core: 1
- Infra-Observability: 3
- Infra-Storage: 3
- Infra-Sync: 4
- Infra-UI: 8
- Plugin-Device: 41
- Plugin-Host: 5
- Plugin-PC: 25
- Processing-Kernel: 25
- Records-Core: 2
- Runtime-Core: 4
- Startup-Core: 12

## Exhaustive File Map (`src/dpost/**/*.py`)
| V1 File | V2 Target | Transform | Lane | Justification |
|---|---|---|---|---|
| `src/dpost/__init__.py` | `src/dpost_v2/__init__.py` | Migrate | Startup-Core | Defines package boundary and exported runtime version surface. |
| `src/dpost/__main__.py` | `src/dpost_v2/__main__.py` | Rewrite | Startup-Core | Defines V2 entrypoint and architecture mode dispatch. |
| `src/dpost/application/__init__.py` | `src/dpost_v2/application/__init__.py` | Migrate | App-Core | Retains application module __init__.py with explicit dependencies. |
| `src/dpost/application/config/__init__.py` | `src/dpost_v2/application/startup/__init__.py` | Move | Startup-Core | Keeps startup package boundary explicit. |
| `src/dpost/application/config/context.py` | `src/dpost_v2/application/startup/context.py` | Retire/Replace | Startup-Core | Replaces ambient global config access with explicit context injection. |
| `src/dpost/application/config/schema.py` | `src/dpost_v2/application/startup/settings_schema.py` | Rename | Startup-Core | Holds typed startup and naming schema definitions. |
| `src/dpost/application/config/service.py` | `src/dpost_v2/application/startup/settings_service.py` | Rename | Startup-Core | Owns validated settings loading and lifecycle API. |
| `src/dpost/application/interactions/__init__.py` | `src/dpost_v2/application/interactions/__init__.py` | Move | Contracts-Core | Retains interaction package boundary. |
| `src/dpost/application/interactions/messages.py` | `src/dpost_v2/application/contracts/events.py` | Move | Contracts-Core | Normalizes interaction messages as shared application events. |
| `src/dpost/application/metrics.py` | `src/dpost_v2/infrastructure/observability/metrics.py` | Move | Infra-Observability | Moves metric emission to observability infrastructure boundary. |
| `src/dpost/application/naming/__init__.py` | `src/dpost_v2/domain/naming/__init__.py` | Merge | Domain-Core | Aligns naming package initialization with domain ownership. |
| `src/dpost/application/naming/policy.py` | `src/dpost_v2/domain/naming/policy.py` | Merge | Domain-Core | Consolidates naming policy logic in pure domain naming package. |
| `src/dpost/application/ports/__init__.py` | `src/dpost_v2/application/contracts/__init__.py` | Move | Contracts-Core | Defines shared contracts package boundary. |
| `src/dpost/application/ports/interactions.py` | `src/dpost_v2/application/contracts/ports.py` | Merge | Contracts-Core | Converges port contract interactions.py into unified ports surface. |
| `src/dpost/application/ports/sync.py` | `src/dpost_v2/application/contracts/ports.py` | Merge | Contracts-Core | Converges port contract sync.py into unified ports surface. |
| `src/dpost/application/ports/ui.py` | `src/dpost_v2/application/contracts/ports.py` | Merge | Contracts-Core | Converges port contract ui.py into unified ports surface. |
| `src/dpost/application/processing/__init__.py` | `src/dpost_v2/application/ingestion/__init__.py` | Migrate | Processing-Kernel | Defines ingestion package boundary. |
| `src/dpost/application/processing/candidate_metadata.py` | `src/dpost_v2/application/ingestion/models/candidate.py` | Move | Processing-Kernel | Defines candidate metadata model for resolve/route. |
| `src/dpost/application/processing/device_resolver.py` | `src/dpost_v2/application/ingestion/stages/resolve.py` | Move | Processing-Kernel | Owns resolve stage for device and plugin matching. |
| `src/dpost/application/processing/error_handling.py` | `src/dpost_v2/application/ingestion/policies/error_handling.py` | Move | Processing-Kernel | Maps exceptions to deterministic pipeline outcomes. |
| `src/dpost/application/processing/failure_emitter.py` | `src/dpost_v2/application/ingestion/policies/failure_emitter.py` | Move | Processing-Kernel | Emits standardized failure events and logs. |
| `src/dpost/application/processing/failure_outcome_policy.py` | `src/dpost_v2/application/ingestion/policies/failure_outcome.py` | Move | Processing-Kernel | Normalizes failure outcome types and handling. |
| `src/dpost/application/processing/file_process_manager.py` | `src/dpost_v2/application/ingestion/engine.py` | Split | Processing-Kernel | Replaces orchestration shell with explicit ingestion engine. |
| `src/dpost/application/processing/file_processor_abstract.py` | `src/dpost_v2/application/contracts/plugin_contracts.py` | Move | Contracts-Core | Moves processor abstraction into plugin contracts. |
| `src/dpost/application/processing/force_path_policy.py` | `src/dpost_v2/application/ingestion/policies/force_path.py` | Move | Processing-Kernel | Defines force-path override policy. |
| `src/dpost/application/processing/immediate_sync_error_emitter.py` | `src/dpost_v2/application/ingestion/policies/immediate_sync_error_emitter.py` | Move | Processing-Kernel | Isolates immediate sync error emission behavior. |
| `src/dpost/application/processing/modified_event_gate.py` | `src/dpost_v2/application/ingestion/policies/modified_event_gate.py` | Move | Processing-Kernel | Debounces duplicate modified events. |
| `src/dpost/application/processing/post_persist_bookkeeping.py` | `src/dpost_v2/application/ingestion/stages/post_persist.py` | Move | Processing-Kernel | Isolates post-persist side effects into dedicated stage. |
| `src/dpost/application/processing/processing_pipeline.py` | `src/dpost_v2/application/ingestion/stages/pipeline.py` | Split | Processing-Kernel | Stage machine remains explicit and independently testable. |
| `src/dpost/application/processing/processing_pipeline_runtime.py` | `src/dpost_v2/application/ingestion/runtime_services.py` | Rename | Processing-Kernel | Defines runtime service facade used by stage machine. |
| `src/dpost/application/processing/processor_factory.py` | `src/dpost_v2/application/ingestion/processor_factory.py` | Move | Processing-Kernel | Selects processor implementation from plugin contracts. |
| `src/dpost/application/processing/processor_runtime_context.py` | `src/dpost_v2/application/contracts/context.py` | Merge | Contracts-Core | Moves runtime context model into shared contract module. |
| `src/dpost/application/processing/record_flow.py` | `src/dpost_v2/application/ingestion/stages/persist.py` | Move | Processing-Kernel | Owns record persistence stage execution path. |
| `src/dpost/application/processing/record_persistence_context.py` | `src/dpost_v2/application/ingestion/stages/persist.py` | Merge | Processing-Kernel | Co-locates persistence context model with persist stage. |
| `src/dpost/application/processing/record_utils.py` | `src/dpost_v2/application/ingestion/stages/persist.py` | Merge | Processing-Kernel | Co-locates persistence helpers with persist stage. |
| `src/dpost/application/processing/rename_flow.py` | `src/dpost_v2/application/ingestion/stages/persist.py` | Merge | Processing-Kernel | Unifies rename flow under persist/failure path. |
| `src/dpost/application/processing/rename_retry_policy.py` | `src/dpost_v2/application/ingestion/policies/retry_planner.py` | Merge | Processing-Kernel | Unifies retry policy in one planner module. |
| `src/dpost/application/processing/route_context_policy.py` | `src/dpost_v2/application/ingestion/stages/route.py` | Merge | Processing-Kernel | Merges route context assembly into route stage. |
| `src/dpost/application/processing/routing.py` | `src/dpost_v2/application/ingestion/stages/route.py` | Move | Processing-Kernel | Owns application route stage orchestration. |
| `src/dpost/application/processing/stability_timing_policy.py` | `src/dpost_v2/application/ingestion/stages/stabilize.py` | Merge | Processing-Kernel | Keeps stabilization timing policy near stabilize stage. |
| `src/dpost/application/processing/stability_tracker.py` | `src/dpost_v2/application/ingestion/stages/stabilize.py` | Merge | Processing-Kernel | Implements stability guard stage logic. |
| `src/dpost/application/records/__init__.py` | `src/dpost_v2/application/records/__init__.py` | Migrate | Records-Core | Retains records package module __init__.py. |
| `src/dpost/application/records/record_manager.py` | `src/dpost_v2/application/records/service.py` | Rename | Records-Core | Defines records service over explicit store contract. |
| `src/dpost/application/retry_delay_policy.py` | `src/dpost_v2/application/ingestion/policies/retry_planner.py` | Merge | Processing-Kernel | Merges legacy retry delay policy into unified planner. |
| `src/dpost/application/runtime/__init__.py` | `src/dpost_v2/application/runtime/__init__.py` | Migrate | Runtime-Core | Retains runtime module __init__.py. |
| `src/dpost/application/runtime/device_watchdog_app.py` | `src/dpost_v2/application/runtime/dpost_app.py` | Rename | Runtime-Core | Keeps top-level dpost app orchestration with explicit collaborators. |
| `src/dpost/application/runtime/retry_planner.py` | `src/dpost_v2/application/ingestion/policies/retry_planner.py` | Move | Processing-Kernel | Shares retry policy with ingestion flow. |
| `src/dpost/application/services/__init__.py` | `src/dpost_v2/application/startup/__init__.py` | Merge | Startup-Core | Merges startup package init into startup boundary. |
| `src/dpost/application/services/runtime_startup.py` | `src/dpost_v2/application/startup/bootstrap.py` | Merge | Startup-Core | Unifies runtime startup orchestration into bootstrap module. |
| `src/dpost/application/session/__init__.py` | `src/dpost_v2/application/session/__init__.py` | Migrate | Runtime-Core | Retains session management module __init__.py in runtime layer. |
| `src/dpost/application/session/session_manager.py` | `src/dpost_v2/application/session/session_manager.py` | Migrate | Runtime-Core | Retains session management module session_manager.py in runtime layer. |
| `src/dpost/device_plugins/__init__.py` | `src/dpost_v2/plugins/devices/__init__.py/` | Migrate | Plugin-Device | Keeps device plugin module  for __init__.py. |
| `src/dpost/device_plugins/dsv_horiba/__init__.py` | `src/dpost_v2/plugins/devices/dsv_horiba/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for dsv_horiba. |
| `src/dpost/device_plugins/dsv_horiba/file_processor.py` | `src/dpost_v2/plugins/devices/dsv_horiba/processor.py` | Rename | Plugin-Device | Keeps device processing logic for dsv_horiba with consistent processor naming. |
| `src/dpost/device_plugins/dsv_horiba/plugin.py` | `src/dpost_v2/plugins/devices/dsv_horiba/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for dsv_horiba. |
| `src/dpost/device_plugins/dsv_horiba/settings.py` | `src/dpost_v2/plugins/devices/dsv_horiba/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for dsv_horiba. |
| `src/dpost/device_plugins/erm_hioki/__init__.py` | `src/dpost_v2/plugins/devices/erm_hioki/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for erm_hioki. |
| `src/dpost/device_plugins/erm_hioki/file_processor.py` | `src/dpost_v2/plugins/devices/erm_hioki/processor.py` | Rename | Plugin-Device | Keeps device processing logic for erm_hioki with consistent processor naming. |
| `src/dpost/device_plugins/erm_hioki/plugin.py` | `src/dpost_v2/plugins/devices/erm_hioki/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for erm_hioki. |
| `src/dpost/device_plugins/erm_hioki/settings.py` | `src/dpost_v2/plugins/devices/erm_hioki/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for erm_hioki. |
| `src/dpost/device_plugins/extr_haake/__init__.py` | `src/dpost_v2/plugins/devices/extr_haake/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for extr_haake. |
| `src/dpost/device_plugins/extr_haake/file_processor.py` | `src/dpost_v2/plugins/devices/extr_haake/processor.py` | Rename | Plugin-Device | Keeps device processing logic for extr_haake with consistent processor naming. |
| `src/dpost/device_plugins/extr_haake/plugin.py` | `src/dpost_v2/plugins/devices/extr_haake/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for extr_haake. |
| `src/dpost/device_plugins/extr_haake/settings.py` | `src/dpost_v2/plugins/devices/extr_haake/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for extr_haake. |
| `src/dpost/device_plugins/psa_horiba/__init__.py` | `src/dpost_v2/plugins/devices/psa_horiba/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for psa_horiba. |
| `src/dpost/device_plugins/psa_horiba/file_processor.py` | `src/dpost_v2/plugins/devices/psa_horiba/processor.py` | Rename | Plugin-Device | Keeps device processing logic for psa_horiba with consistent processor naming. |
| `src/dpost/device_plugins/psa_horiba/plugin.py` | `src/dpost_v2/plugins/devices/psa_horiba/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for psa_horiba. |
| `src/dpost/device_plugins/psa_horiba/settings.py` | `src/dpost_v2/plugins/devices/psa_horiba/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for psa_horiba. |
| `src/dpost/device_plugins/rhe_kinexus/__init__.py` | `src/dpost_v2/plugins/devices/rhe_kinexus/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for rhe_kinexus. |
| `src/dpost/device_plugins/rhe_kinexus/file_processor.py` | `src/dpost_v2/plugins/devices/rhe_kinexus/processor.py` | Rename | Plugin-Device | Keeps device processing logic for rhe_kinexus with consistent processor naming. |
| `src/dpost/device_plugins/rhe_kinexus/plugin.py` | `src/dpost_v2/plugins/devices/rhe_kinexus/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for rhe_kinexus. |
| `src/dpost/device_plugins/rhe_kinexus/settings.py` | `src/dpost_v2/plugins/devices/rhe_kinexus/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for rhe_kinexus. |
| `src/dpost/device_plugins/rmx_eirich_el1/__init__.py` | `src/dpost_v2/plugins/devices/rmx_eirich_el1/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for rmx_eirich_el1. |
| `src/dpost/device_plugins/rmx_eirich_el1/file_processor.py` | `src/dpost_v2/plugins/devices/rmx_eirich_el1/processor.py` | Rename | Plugin-Device | Keeps device processing logic for rmx_eirich_el1 with consistent processor naming. |
| `src/dpost/device_plugins/rmx_eirich_el1/plugin.py` | `src/dpost_v2/plugins/devices/rmx_eirich_el1/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for rmx_eirich_el1. |
| `src/dpost/device_plugins/rmx_eirich_el1/settings.py` | `src/dpost_v2/plugins/devices/rmx_eirich_el1/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for rmx_eirich_el1. |
| `src/dpost/device_plugins/rmx_eirich_r01/__init__.py` | `src/dpost_v2/plugins/devices/rmx_eirich_r01/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for rmx_eirich_r01. |
| `src/dpost/device_plugins/rmx_eirich_r01/file_processor.py` | `src/dpost_v2/plugins/devices/rmx_eirich_r01/processor.py` | Rename | Plugin-Device | Keeps device processing logic for rmx_eirich_r01 with consistent processor naming. |
| `src/dpost/device_plugins/rmx_eirich_r01/plugin.py` | `src/dpost_v2/plugins/devices/rmx_eirich_r01/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for rmx_eirich_r01. |
| `src/dpost/device_plugins/rmx_eirich_r01/settings.py` | `src/dpost_v2/plugins/devices/rmx_eirich_r01/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for rmx_eirich_r01. |
| `src/dpost/device_plugins/sem_phenomxl2/__init__.py` | `src/dpost_v2/plugins/devices/sem_phenomxl2/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for sem_phenomxl2. |
| `src/dpost/device_plugins/sem_phenomxl2/file_processor.py` | `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py` | Rename | Plugin-Device | Keeps device processing logic for sem_phenomxl2 with consistent processor naming. |
| `src/dpost/device_plugins/sem_phenomxl2/plugin.py` | `src/dpost_v2/plugins/devices/sem_phenomxl2/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for sem_phenomxl2. |
| `src/dpost/device_plugins/sem_phenomxl2/settings.py` | `src/dpost_v2/plugins/devices/sem_phenomxl2/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for sem_phenomxl2. |
| `src/dpost/device_plugins/test_device/__init__.py` | `src/dpost_v2/plugins/devices/test_device/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for test_device. |
| `src/dpost/device_plugins/test_device/file_processor.py` | `src/dpost_v2/plugins/devices/test_device/processor.py` | Rename | Plugin-Device | Keeps device processing logic for test_device with consistent processor naming. |
| `src/dpost/device_plugins/test_device/plugin.py` | `src/dpost_v2/plugins/devices/test_device/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for test_device. |
| `src/dpost/device_plugins/test_device/settings.py` | `src/dpost_v2/plugins/devices/test_device/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for test_device. |
| `src/dpost/device_plugins/utm_zwick/__init__.py` | `src/dpost_v2/plugins/devices/utm_zwick/__init__.py` | Migrate | Plugin-Device | Keeps device plugin module __init__.py for utm_zwick. |
| `src/dpost/device_plugins/utm_zwick/file_processor.py` | `src/dpost_v2/plugins/devices/utm_zwick/processor.py` | Rename | Plugin-Device | Keeps device processing logic for utm_zwick with consistent processor naming. |
| `src/dpost/device_plugins/utm_zwick/plugin.py` | `src/dpost_v2/plugins/devices/utm_zwick/plugin.py` | Migrate | Plugin-Device | Keeps device plugin module plugin.py for utm_zwick. |
| `src/dpost/device_plugins/utm_zwick/settings.py` | `src/dpost_v2/plugins/devices/utm_zwick/settings.py` | Migrate | Plugin-Device | Keeps device plugin module settings.py for utm_zwick. |
| `src/dpost/domain/__init__.py` | `src/dpost_v2/domain/__init__.py` | Migrate | Domain-Core | Retains pure domain module __init__.py. |
| `src/dpost/domain/naming/__init__.py` | `src/dpost_v2/domain/naming/__init__.py` | Migrate | Domain-Core | Retains pure naming rule module __init__.py. |
| `src/dpost/domain/naming/identifiers.py` | `src/dpost_v2/domain/naming/identifiers.py` | Migrate | Domain-Core | Retains pure naming rule module identifiers.py. |
| `src/dpost/domain/naming/prefix_policy.py` | `src/dpost_v2/domain/naming/prefix_policy.py` | Migrate | Domain-Core | Retains pure naming rule module prefix_policy.py. |
| `src/dpost/domain/processing/__init__.py` | `src/dpost_v2/domain/processing/__init__.py` | Migrate | Domain-Core | Retains processing domain model or policy __init__.py. |
| `src/dpost/domain/processing/batch_models.py` | `src/dpost_v2/domain/processing/batch_models.py` | Migrate | Domain-Core | Retains processing domain model or policy batch_models.py. |
| `src/dpost/domain/processing/models.py` | `src/dpost_v2/domain/processing/models.py` | Migrate | Domain-Core | Retains processing domain model or policy models.py. |
| `src/dpost/domain/processing/routing.py` | `src/dpost_v2/domain/routing/rules.py` | Move | Domain-Core | Moves routing rules into dedicated domain routing module. |
| `src/dpost/domain/processing/staging.py` | `src/dpost_v2/domain/processing/staging.py` | Migrate | Domain-Core | Retains processing domain model or policy staging.py. |
| `src/dpost/domain/processing/text.py` | `src/dpost_v2/domain/processing/text.py` | Migrate | Domain-Core | Retains processing domain model or policy text.py. |
| `src/dpost/domain/records/__init__.py` | `src/dpost_v2/domain/records/__init__.py` | Migrate | Domain-Core | Retains record entity contract __init__.py in domain layer. |
| `src/dpost/domain/records/local_record.py` | `src/dpost_v2/domain/records/local_record.py` | Migrate | Domain-Core | Retains record entity contract local_record.py in domain layer. |
| `src/dpost/infrastructure/__init__.py` | `src/dpost_v2/infrastructure/__init__.py` | Migrate | Infra-Core | Retains infrastructure module __init__.py with explicit adapter ownership. |
| `src/dpost/infrastructure/logging.py` | `src/dpost_v2/infrastructure/observability/logging.py` | Move | Infra-Observability | Moves logging config to observability package. |
| `src/dpost/infrastructure/observability.py` | `src/dpost_v2/infrastructure/observability/tracing.py` | Split | Infra-Observability | Separates tracing/event concerns under observability package. |
| `src/dpost/infrastructure/runtime_adapters/__init__.py` | `src/dpost_v2/infrastructure/runtime/ui/__init__.py` | Move | Infra-UI | Moves UI runtime adapter __init__.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/desktop_ui.py` | `src/dpost_v2/infrastructure/runtime/ui/desktop.py` | Move | Infra-UI | Moves UI runtime adapter desktop_ui.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/dialogs.py` | `src/dpost_v2/infrastructure/runtime/ui/dialogs.py` | Move | Infra-UI | Moves UI runtime adapter dialogs.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/headless_ui.py` | `src/dpost_v2/infrastructure/runtime/ui/headless.py` | Move | Infra-UI | Moves UI runtime adapter headless_ui.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py` | `src/dpost_v2/infrastructure/runtime/ui/startup_dependencies.py` | Move | Infra-UI | Moves UI runtime adapter startup_dependencies.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/tkinter_ui.py` | `src/dpost_v2/infrastructure/runtime/ui/tkinter.py` | Move | Infra-UI | Moves UI runtime adapter tkinter_ui.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/ui_adapters.py` | `src/dpost_v2/infrastructure/runtime/ui/adapters.py` | Move | Infra-UI | Moves UI runtime adapter ui_adapters.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/runtime_adapters/ui_factory.py` | `src/dpost_v2/infrastructure/runtime/ui/factory.py` | Move | Infra-UI | Moves UI runtime adapter ui_factory.py to dedicated UI infrastructure lane. |
| `src/dpost/infrastructure/storage/__init__.py` | `src/dpost_v2/infrastructure/storage/__init__.py` | Migrate | Infra-Storage | Retains storage adapter module __init__.py. |
| `src/dpost/infrastructure/storage/filesystem_utils.py` | `src/dpost_v2/infrastructure/storage/file_ops.py` | Split | Infra-Storage | Narrows broad helper surface into explicit context-driven file ops. |
| `src/dpost/infrastructure/storage/staging_dirs.py` | `src/dpost_v2/infrastructure/storage/staging_dirs.py` | Migrate | Infra-Storage | Retains storage adapter module staging_dirs.py. |
| `src/dpost/infrastructure/sync/__init__.py` | `src/dpost_v2/infrastructure/sync/__init__.py` | Migrate | Infra-Sync | Retains sync adapter module __init__.py. |
| `src/dpost/infrastructure/sync/kadi.py` | `src/dpost_v2/infrastructure/sync/kadi.py` | Merge | Infra-Sync | Consolidates Kadi sync integration into one adapter module. |
| `src/dpost/infrastructure/sync/kadi_manager.py` | `src/dpost_v2/infrastructure/sync/kadi.py` | Merge | Infra-Sync | Consolidates Kadi sync integration into one adapter module. |
| `src/dpost/infrastructure/sync/noop.py` | `src/dpost_v2/infrastructure/sync/noop.py` | Migrate | Infra-Sync | Retains sync adapter module noop.py. |
| `src/dpost/pc_plugins/__init__.py` | `src/dpost_v2/plugins/pcs/__init__.py/` | Migrate | Plugin-PC | Keeps PC plugin module  for __init__.py. |
| `src/dpost/pc_plugins/eirich_blb/__init__.py` | `src/dpost_v2/plugins/pcs/eirich_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for eirich_blb. |
| `src/dpost/pc_plugins/eirich_blb/plugin.py` | `src/dpost_v2/plugins/pcs/eirich_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for eirich_blb. |
| `src/dpost/pc_plugins/eirich_blb/settings.py` | `src/dpost_v2/plugins/pcs/eirich_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for eirich_blb. |
| `src/dpost/pc_plugins/haake_blb/__init__.py` | `src/dpost_v2/plugins/pcs/haake_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for haake_blb. |
| `src/dpost/pc_plugins/haake_blb/plugin.py` | `src/dpost_v2/plugins/pcs/haake_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for haake_blb. |
| `src/dpost/pc_plugins/haake_blb/settings.py` | `src/dpost_v2/plugins/pcs/haake_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for haake_blb. |
| `src/dpost/pc_plugins/hioki_blb/__init__.py` | `src/dpost_v2/plugins/pcs/hioki_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for hioki_blb. |
| `src/dpost/pc_plugins/hioki_blb/plugin.py` | `src/dpost_v2/plugins/pcs/hioki_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for hioki_blb. |
| `src/dpost/pc_plugins/hioki_blb/settings.py` | `src/dpost_v2/plugins/pcs/hioki_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for hioki_blb. |
| `src/dpost/pc_plugins/horiba_blb/__init__.py` | `src/dpost_v2/plugins/pcs/horiba_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for horiba_blb. |
| `src/dpost/pc_plugins/horiba_blb/plugin.py` | `src/dpost_v2/plugins/pcs/horiba_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for horiba_blb. |
| `src/dpost/pc_plugins/horiba_blb/settings.py` | `src/dpost_v2/plugins/pcs/horiba_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for horiba_blb. |
| `src/dpost/pc_plugins/kinexus_blb/__init__.py` | `src/dpost_v2/plugins/pcs/kinexus_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for kinexus_blb. |
| `src/dpost/pc_plugins/kinexus_blb/plugin.py` | `src/dpost_v2/plugins/pcs/kinexus_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for kinexus_blb. |
| `src/dpost/pc_plugins/kinexus_blb/settings.py` | `src/dpost_v2/plugins/pcs/kinexus_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for kinexus_blb. |
| `src/dpost/pc_plugins/test_pc/__init__.py` | `src/dpost_v2/plugins/pcs/test_pc/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for test_pc. |
| `src/dpost/pc_plugins/test_pc/plugin.py` | `src/dpost_v2/plugins/pcs/test_pc/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for test_pc. |
| `src/dpost/pc_plugins/test_pc/settings.py` | `src/dpost_v2/plugins/pcs/test_pc/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for test_pc. |
| `src/dpost/pc_plugins/tischrem_blb/__init__.py` | `src/dpost_v2/plugins/pcs/tischrem_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for tischrem_blb. |
| `src/dpost/pc_plugins/tischrem_blb/plugin.py` | `src/dpost_v2/plugins/pcs/tischrem_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for tischrem_blb. |
| `src/dpost/pc_plugins/tischrem_blb/settings.py` | `src/dpost_v2/plugins/pcs/tischrem_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for tischrem_blb. |
| `src/dpost/pc_plugins/zwick_blb/__init__.py` | `src/dpost_v2/plugins/pcs/zwick_blb/__init__.py` | Migrate | Plugin-PC | Keeps PC plugin module __init__.py for zwick_blb. |
| `src/dpost/pc_plugins/zwick_blb/plugin.py` | `src/dpost_v2/plugins/pcs/zwick_blb/plugin.py` | Migrate | Plugin-PC | Keeps PC plugin module plugin.py for zwick_blb. |
| `src/dpost/pc_plugins/zwick_blb/settings.py` | `src/dpost_v2/plugins/pcs/zwick_blb/settings.py` | Migrate | Plugin-PC | Keeps PC plugin module settings.py for zwick_blb. |
| `src/dpost/plugins/__init__.py` | `src/dpost_v2/plugins/__init__.py` | Migrate | Plugin-Host | Maintains plugin host package boundary. |
| `src/dpost/plugins/contracts.py` | `src/dpost_v2/application/contracts/plugin_contracts.py` | Move | Contracts-Core | Promotes plugin contract model to contract-first application boundary. |
| `src/dpost/plugins/loading.py` | `src/dpost_v2/plugins/discovery.py` | Rename | Plugin-Host | Renames loader to explicit discovery module. |
| `src/dpost/plugins/profile_selection.py` | `src/dpost_v2/plugins/profile_selection.py` | Migrate | Plugin-Host | Retains profile-based plugin selection logic. |
| `src/dpost/plugins/reference.py` | `src/dpost_v2/plugins/catalog.py` | Rename | Plugin-Host | Renames reference to catalog metadata module. |
| `src/dpost/plugins/system.py` | `src/dpost_v2/plugins/host.py` | Rename | Plugin-Host | Renames plugin system to host lifecycle module. |
| `src/dpost/runtime/__init__.py` | `src/dpost_v2/runtime/__init__.py` | Migrate | Startup-Core | Retains runtime assembly module __init__.py with clearer ownership. |
| `src/dpost/runtime/bootstrap.py` | `src/dpost_v2/application/startup/bootstrap.py` | Split | Startup-Core | Moves startup flow into explicit application startup boundary. |
| `src/dpost/runtime/composition.py` | `src/dpost_v2/runtime/composition.py` | Rewrite | Startup-Core | Composition root wires contracts to adapters for V2. |
| `src/dpost/runtime/startup_config.py` | `src/dpost_v2/application/startup/settings.py` | Split | Startup-Core | Centralizes startup settings parsing and validation. |

## References
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/pseudocode/README.md`
- `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`
- `docs/planning/archive/20260303-processing-sprawl-posture-rpc.md`
- `docs/planning/archive/20260224-naming-settings-single-source-of-truth-rpc.md`

