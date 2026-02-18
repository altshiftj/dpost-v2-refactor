# Responsibility Catalog

## Purpose
- Define clear ownership boundaries for major objects/modules.
- Reduce overlap and ambiguity during migration refactors.

## Catalog
| Object/Module | Layer | Primary Responsibility | Owns | Must Not Own |
|---|---|---|---|---|
| `bootstrap` | Application/Infrastructure boundary | Compose runtime dependencies and startup settings | Runtime wiring, startup validation | Device-specific business rules |
| `DeviceWatchdogApp` | Application | Coordinate observer lifecycle and queue-driven processing loop | Event queue polling, graceful shutdown orchestration | Direct plugin discovery logic |
| `FileProcessManager` | Application | Execute artifact processing workflow end-to-end | Pipeline orchestration and result handling | Low-level transport/backend API details |
| `DeviceResolver` | Application | Select correct device for artifact using selectors + probe hints | Candidate resolution logic | File movement and persistence side effects |
| `FileProcessorABS` + concrete processors | Plugins | Apply device-specific preprocessing and processing | Device-format handling rules | Global runtime wiring |
| `ConfigService` | Domain/Application support | Provide active PC/device configuration context | Config registration and activation scope | Filesystem mutation side effects |
| `RecordManager` | Application | Manage local record lifecycle and persistence delegation | Record creation, lookup, sync trigger calls | Device-specific parsing |
| `LocalRecord` | Domain model | Represent per-record metadata and file upload state | Record state and sync flags | Backend API operations |
| `ISyncManager` | Application port | Define sync backend contract | Sync abstraction boundary | UI event-loop concerns |
| `KadiSyncManager` | Infrastructure adapter | Implement sync backend against Kadi | Kadi API mapping and upload calls | Core processing orchestration |
| `PluginLoader` | Infrastructure support | Register/discover/instantiate device and PC plugins | Plugin lifecycle and registration state | Artifact processing behavior |
| `UserInteractionPort` + adapters | Application port + Infrastructure adapter | Decouple interaction requests from UI implementation | Interaction contract and adapter mapping | Core domain decision logic |

## Responsibility Rules
1. Application orchestrators can call ports, not concrete infrastructure by default.
2. Plugins can provide domain behavior for devices, but not global runtime wiring.
3. Infrastructure adapters can depend on external SDKs/APIs, but domain models cannot.
4. New component ownership changes must update this catalog in the same change set.

