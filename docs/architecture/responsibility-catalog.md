# Responsibility Catalog

## Purpose
- Define clear ownership boundaries for major objects/modules.
- Reduce overlap and ambiguity during migration refactors.

## Catalog
| Object/Module | Layer | Primary Responsibility | Owns | Must Not Own |
|---|---|---|---|---|
| `bootstrap` | Application/Infrastructure boundary | Compose runtime dependencies and startup settings | Runtime wiring, startup validation | Device-specific business rules |
| `dpost.runtime.composition` | Runtime kernel boundary | Resolve runtime mode, adapter/profile selection, and delegate bootstrap wiring | Startup composition policy and env-to-contract mapping, explicit UI factory selection | Concrete backend SDK imports or plugin discovery logic |
| `dpost.application.services.runtime_startup` | Application service | Orchestrate runtime bootstrap argument composition from selected runtime policies | Runtime startup orchestration and argument precedence policy | Environment parsing and concrete legacy module imports |
| `dpost.runtime.bootstrap` | Runtime kernel boundary | Define native startup contracts and bootstrap boundary API for dpost entry/runtime composition | dpost startup settings/context/error contract surface | Direct legacy bootstrap module-path imports in composition or entry modules |
| `dpost.runtime.startup_config` | Runtime boundary helper | Resolve startup settings from env/overrides into runtime bootstrap settings contract | Startup env parsing and port-validation policy | Composition root selection policy and concrete backend imports |
| `dpost.infrastructure.runtime.legacy_bootstrap_adapter` | Infrastructure adapter | Encapsulate legacy bootstrap module delegation behind infrastructure-owned adapter calls | Legacy bootstrap access path and lazy symbol resolution | Runtime composition policy and startup env resolution ownership |
| `dpost.infrastructure.runtime.ui_factory` | Infrastructure adapter | Resolve mode-specific UI factory implementations for runtime composition | Headless/desktop UI factory mapping and lazy desktop import path | Runtime mode decision policy |
| `dpost.plugins.profile_selection` | Plugin boundary helper | Resolve configured plugin profile names to plugin-profile contracts | Plugin profile name mapping and actionable unknown-profile errors | Runtime bootstrap wiring and env-to-settings composition |
| `dpost.infrastructure.logging` | Infrastructure adapter | Expose canonical logging setup for dpost startup modules | Startup logging adapter boundary | Runtime orchestration and legacy bootstrap wiring policy |
| `DeviceWatchdogApp` | Application | Coordinate observer lifecycle and queue-driven processing loop | Event queue polling, graceful shutdown orchestration | Direct plugin discovery logic |
| `FileProcessManager` | Application | Execute artifact processing workflow end-to-end | Pipeline orchestration, stage sequencing, and result handling | Low-level transport/backend API details |
| `_ProcessingPipeline` | Application (internal helper) | Sequence stage transitions for a single artifact | Resolve/stabilize/preprocess/route-decision/non-ACCEPT-route and persist-stage control flow | Direct record persistence implementation details |
| `DeviceResolver` | Application | Select correct device for artifact using selectors + probe hints | Candidate resolution logic | File movement and persistence side effects |
| `FileProcessorABS` + concrete processors | Plugins | Apply device-specific preprocessing and processing | Device-format handling rules | Global runtime wiring |
| `ConfigService` | Domain/Application support | Provide active PC/device configuration context | Config registration and activation scope | Filesystem mutation side effects |
| `RecordManager` | Application | Manage local record lifecycle and persistence delegation | Record creation, lookup, sync trigger calls | Device-specific parsing |
| `LocalRecord` | Domain model | Represent per-record metadata and file upload state | Record state and sync flags | Backend API operations |
| `ISyncManager` | Application port | Define sync backend contract | Sync abstraction boundary | UI event-loop concerns |
| `SyncAdapterPort` | Application port | Define dpost sync adapter contract for framework composition paths | Adapter behavior contract for sync calls | Concrete backend SDK imports |
| `PluginProfile` + `REFERENCE_PLUGIN_PROFILE` | Plugin reference contract | Define a backend-agnostic plugin profile for kernel validation startup paths | Test-safe PC/device plugin identifiers | Runtime orchestration and concrete backend coupling |
| `KadiSyncManager` | Infrastructure adapter | Implement sync backend against Kadi | Kadi API mapping and upload calls | Core processing orchestration |
| `KadiSyncAdapter` | Infrastructure adapter (dpost wrapper) | Bridge dpost sync port to legacy Kadi implementation with optional dependency handling | Adapter selection path and lazy legacy delegation | Runtime composition policy |
| `NoopSyncAdapter` | Infrastructure adapter (reference) | Provide no-op sync behavior for framework validation and local headless paths | Deterministic no-op sync responses | Production backend side effects |
| `HeadlessRuntimeUI` | Infrastructure adapter (runtime UI) | Provide non-interactive UI/scheduler behavior for headless runtime mode | Headless event-loop scheduling and no-dialog interaction defaults | Desktop dialog rendering and Tk lifecycle ownership |
| `PluginLoader` | Infrastructure support | Register/discover/instantiate device and PC plugins | Plugin lifecycle and registration state | Artifact processing behavior |
| `UserInteractionPort` + adapters | Application port + Infrastructure adapter | Decouple interaction requests from UI implementation | Interaction contract and adapter mapping | Core domain decision logic |

## Responsibility Rules
1. Application orchestrators can call ports, not concrete infrastructure by default.
2. Plugins can provide domain behavior for devices, but not global runtime wiring.
3. Infrastructure adapters can depend on external SDKs/APIs, but domain models cannot.
4. New component ownership changes must update this catalog in the same change set.
