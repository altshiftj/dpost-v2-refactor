# Responsibility Catalog

## Purpose
- Define clear ownership boundaries for major objects/modules.
- Reduce overlap and ambiguity during runtime refactors.

## Catalog
| Object/Module | Layer | Primary Responsibility | Owns | Must Not Own |
|---|---|---|---|---|
| `bootstrap` | Application/Infrastructure boundary | Compose runtime dependencies and startup settings | Runtime wiring, startup validation | Device-specific business rules |
| `dpost.runtime.composition` | Runtime kernel boundary | Resolve runtime mode, adapter/profile selection, and delegate bootstrap wiring | Startup composition policy and env-to-contract mapping, explicit UI factory selection | Concrete backend SDK imports or plugin discovery logic |
| `dpost.application.services.runtime_startup` | Application service | Orchestrate runtime bootstrap argument composition from selected runtime policies | Runtime startup orchestration and argument precedence policy | Environment parsing and concrete legacy module imports |
| `dpost.runtime.bootstrap` | Runtime kernel boundary | Define native startup contracts and bootstrap boundary API for dpost entry/runtime composition | dpost startup settings/context/error contract surface | Direct legacy bootstrap module-path imports in composition or entry modules |
| `dpost.infrastructure.runtime.bootstrap_dependencies` | Infrastructure adapter | Own runtime bootstrap dependency construction for config, UI adapters, sync manager, and app object wiring | Runtime dependency factories and startup adapter bindings | Startup settings policy and composition-root selection logic |
| `dpost.infrastructure.runtime.desktop_ui` | Infrastructure adapter | Resolve desktop UI class behind a dpost-owned runtime boundary | Desktop UI class resolution and lazy loading seam | Runtime mode decision policy |
| `dpost.infrastructure.runtime.tkinter_ui` | Infrastructure adapter | Implement desktop Tk runtime UI against dpost UI contracts | Tk lifecycle, desktop dialogs, scheduling, and interaction hooks | Runtime composition policy and startup settings decisions |
| `dpost.infrastructure.runtime.dialogs` | Infrastructure adapter | Provide desktop rename dialog widgets for runtime UI flows | Rename dialog rendering, validation messaging, and Tk form controls | Runtime mode decision policy and processing orchestration |
| `dpost.runtime.startup_config` | Runtime boundary helper | Resolve startup settings from env/overrides into runtime bootstrap settings contract | Startup env parsing and port-validation policy | Composition root selection policy and concrete backend imports |
| `dpost.infrastructure.runtime.ui_factory` | Infrastructure adapter | Resolve mode-specific UI factory implementations for runtime composition | Headless/desktop UI factory mapping and lazy desktop import path | Runtime mode decision policy |
| `dpost.infrastructure.runtime.ui_adapters` | Infrastructure adapter | Bridge interaction/task-scheduler ports onto runtime UI implementations | Interaction adapter and scheduler adapter implementations | Runtime mode selection and startup policy |
| `dpost.plugins.profile_selection` | Plugin boundary helper | Resolve configured plugin profile names to plugin-profile contracts | Plugin profile name mapping and actionable unknown-profile errors | Runtime bootstrap wiring and env-to-settings composition |
| `dpost.plugins.loading` | Plugin boundary helper | Resolve PC/device plugin instances through canonical dpost plugin loading APIs | Plugin lookup calls used by runtime bootstrap and config wiring | Runtime mode/adapter selection policy |
| `dpost.plugins.contracts` | Plugin contract | Define dpost-owned structural plugin protocol types for loader boundaries | Runtime-checkable plugin type contracts (`DevicePlugin.get_config`, `DevicePlugin.get_file_processor`, `PCPlugin.get_config`) and decoupled typing surface | Concrete plugin discovery implementation |
| `dpost.infrastructure.logging` | Infrastructure adapter | Provide canonical dpost logger configuration implementation | JSON logger formatter and rotating handler setup | Runtime orchestration policy |
| `dpost.infrastructure.observability` | Infrastructure adapter | Provide canonical observability HTTP server wiring for runtime bootstrap | `/health` and `/logs` server lifecycle wiring | Runtime startup policy and plugin/config resolution |
| `dpost.application.runtime.DeviceWatchdogApp` | Application | Coordinate observer lifecycle and queue-driven processing loop | Event queue polling, graceful shutdown orchestration | Direct plugin discovery logic |
| `dpost.application.ports.ui` | Application port | Define dpost-owned UI interaction contract types used by runtime adapters | User-interface typing contracts and session prompt model | Concrete UI framework imports |
| `dpost.application.ports.interactions` | Application port | Define dpost-owned interaction and scheduler contracts for runtime flows | Rename/session interaction contracts and scheduler abstractions | Concrete UI framework imports |
| `dpost.application.interactions.messages` | Application support | Own canonical runtime/user-facing message catalog constants for dpost app flows | Error/warning/info/prompt message constants | UI-framework rendering concerns |
| `dpost.application.processing.FileProcessManager` | Application | Execute artifact processing workflow end-to-end | Pipeline orchestration, stage sequencing, and result handling | Low-level transport/backend API details |
| `dpost.application.processing._ProcessingPipeline` | Application (internal helper) | Sequence stage transitions for a single artifact | Resolve/stabilize/preprocess/route-decision/non-ACCEPT-route and persist-stage control flow | Direct record persistence implementation details |
| `dpost.domain.processing.models` | Domain model | Define processing request/candidate/result models and routing status enums | Processing value contracts and route context state | Filesystem mutation, record lookup, UI prompts |
| `dpost.domain.processing.batch_models` | Domain model | Define staged batch value types shared by plugin preprocessors | Pending/staged pair value contracts and flush batch grouping | Filesystem mutation and orchestration flow control |
| `dpost.domain.processing.routing` | Domain policy | Decide routing outcomes from record state, naming validity, and appendability contract | Pure routing decision policy | Record lookup/storage operations, workflow side effects |
| `dpost.domain.processing.staging` | Domain policy | Reconstruct staged left/right artefact pairs and stale-stage eligibility policy | Pair reconstruction and stale-stage policy logic | Stage directory creation/mutation and logging side effects |
| `dpost.domain.processing.text` | Domain policy | Decode text prefixes with deterministic encoding/fallback policy | Text decode fallback policy for plugin probes/parsing | File movement, orchestration flow control, runtime wiring |
| `dpost.domain.naming.prefix_policy` | Domain policy | Validate/sanitize naming prefixes and explain naming rule violations | Pure naming-prefix validation and violation analysis policy | Runtime config access, filesystem mutation, orchestration control flow |
| `dpost.domain.naming.identifiers` | Domain policy | Parse filenames and compose record/file identifiers from naming settings | Pure parse and identifier composition policy | Runtime config access, filesystem mutation, orchestration control flow |
| `dpost.application.naming.policy` | Application support | Apply active runtime naming configuration to domain naming policy helpers | Config-aware naming facade for routing, rename flow, processing manager, and plugins | Filesystem side effects and low-level path mutation |
| `dpost.application.processing.DeviceResolver` | Application | Select correct device for artifact using selectors + probe hints | Candidate resolution logic | File movement and persistence side effects |
| `dpost.infrastructure.storage.staging_dirs` | Infrastructure adapter | Create unique staging directories for plugin preprocessors that batch filesystem artifacts | Stage-directory creation/mutation behavior and uniqueness policy | Domain routing/appendability policy and runtime composition wiring |
| `dpost.infrastructure.storage.filesystem_utils` | Infrastructure adapter | Provide canonical storage/path utility behavior for dpost processing and records flows | Directory init, path/move helpers, and record persistence serialization | Runtime composition policy, domain naming parse/identifier policy, and device-processing orchestration |
| `dpost.application.config` | Application support | Own config schemas, service, and runtime accessor lifecycle for canonical dpost paths | Config dataclasses, active config context, init/current/activate runtime helpers | Direct plugin discovery or runtime composition policy |
| `dpost.application.metrics` | Application support | Own canonical metric definitions for dpost runtime/application paths | Counter/gauge/histogram definitions with registry-safe reuse | Runtime orchestration policy and plugin/config resolution |
| `FileProcessorABS` + concrete processors | Plugins | Apply device-specific preprocessing and processing | Device-format handling rules | Global runtime wiring |
| `ConfigService` | Domain/Application support | Provide active PC/device configuration context | Config registration and activation scope | Filesystem mutation side effects |
| `RecordManager` | Application | Manage local record lifecycle and persistence delegation | Record creation, lookup, sync trigger calls | Device-specific parsing |
| `dpost.domain.records.local_record.LocalRecord` | Domain model | Represent per-record metadata and file upload state | Record state and sync flags | Backend API operations |
| `ISyncManager` | Application port | Define sync backend contract | Sync abstraction boundary | UI event-loop concerns |
| `SyncAdapterPort` | Application port | Define dpost sync adapter contract for framework composition paths | Adapter behavior contract for sync calls | Concrete backend SDK imports |
| `PluginProfile` + `REFERENCE_PLUGIN_PROFILE` | Plugin reference contract | Define a backend-agnostic plugin profile for kernel validation startup paths | Test-safe PC/device plugin identifiers | Runtime orchestration and concrete backend coupling |
| `KadiSyncManager` | Infrastructure adapter | Implement sync backend against Kadi | Kadi API mapping and upload calls | Core processing orchestration |
| `KadiSyncAdapter` | Infrastructure adapter (dpost wrapper) | Bridge dpost sync port to Kadi sync manager implementation with optional dependency handling | Adapter selection path and lazy `KadiSyncManager` delegation | Runtime composition policy |
| `NoopSyncAdapter` | Infrastructure adapter (reference) | Provide no-op sync behavior for framework validation and local headless paths | Deterministic no-op sync responses | Production backend side effects |
| `HeadlessRuntimeUI` | Infrastructure adapter (runtime UI) | Provide non-interactive UI/scheduler behavior for headless runtime mode | Headless event-loop scheduling and no-dialog interaction defaults | Desktop dialog rendering and Tk lifecycle ownership |
| `dpost.plugins.system.PluginLoader` | Infrastructure support | Register/discover/instantiate device and PC plugins | Plugin lifecycle and registration state with canonical dpost groups and canonical hook namespace | Artifact processing behavior |
| `UserInteractionPort` + adapters | Application port + Infrastructure adapter | Decouple interaction requests from UI implementation | Interaction contract and adapter mapping | Core domain decision logic |

## Responsibility Rules
1. Application orchestrators can call ports, not concrete infrastructure by default.
2. Plugins can provide domain behavior for devices, but not global runtime wiring.
3. Infrastructure adapters can depend on external SDKs/APIs, but domain models cannot.
4. New component ownership changes must update this catalog in the same change set.
