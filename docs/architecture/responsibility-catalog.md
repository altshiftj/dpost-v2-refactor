# Responsibility Catalog

## Purpose

- Keep module ownership explicit for active V2 runtime surfaces.
- Reduce overlap across layers and simplify review/maintenance.

## Catalog

| Object/Module | Layer | Primary Responsibility | Owns | Must Not Own |
|---|---|---|---|---|
| `dpost_v2.__main__` | Entrypoint | Parse CLI/environment startup input and trigger bootstrap | Process entrypoint normalization and exit-code mapping | Runtime composition internals |
| `dpost_v2.application.startup.bootstrap` | Application | Orchestrate startup sequence (settings -> dependencies -> context -> composition -> launch) | Startup result/failure/event flow | Concrete infrastructure wiring details |
| `dpost_v2.application.startup.settings_service` | Application | Load/normalize startup settings | Settings load policy and cache behavior | Adapter implementation logic |
| `dpost_v2.application.startup.context` | Application contract helper | Validate startup context coherence | Launch/settings/dependency context integrity | Composition of concrete adapters |
| `dpost_v2.runtime.startup_dependencies` | Runtime/Infrastructure boundary | Resolve backend selections into dependency factories | Backend token validation and compatibility checks | Domain/application business decisions |
| `dpost_v2.runtime.composition` | Runtime | Build runtime bundle and validate port bindings | Adapter instantiation order and runtime app wiring | Domain policy and plugin business logic |
| `dpost_v2.application.runtime.dpost_app` | Application | Coordinate session/runtime lifecycle and ingestion dispatch | Runtime loop orchestration and event handling | Concrete plugin discovery implementation |
| `dpost_v2.application.ingestion.engine` | Application | Execute end-to-end ingestion flow | Stage sequencing and ingestion outcomes | Filesystem/backend adapter implementation |
| `dpost_v2.application.ingestion.runtime_services` | Application support | Provide ingestion runtime collaborator access | Runtime service adapters consumed by stages | Domain policy ownership |
| `dpost_v2.application.records.service` | Application | Manage record persistence lifecycle through ports | Record update/save flow | Low-level storage backend implementation |
| `dpost_v2.application.contracts.ports` | Application contracts | Define stable adapter interfaces/results | Port contracts and binding validation | Concrete adapter code |
| `dpost_v2.application.contracts.plugin_contracts` | Application contracts | Define plugin metadata/capability/processor contracts | Plugin contract validation and compatibility checks | Discovery/runtime composition logic |
| `dpost_v2.domain.processing.*` | Domain | Pure processing models/policies | Processing data semantics and pure rules | IO/runtime side effects |
| `dpost_v2.domain.naming.*` | Domain | Pure naming and identifier policy | Prefix/identifier parsing and validation semantics | Config/runtime adapters |
| `dpost_v2.domain.routing.rules` | Domain | Pure route-decision policy | Route outcome rules independent of infrastructure | Persistence/sync side effects |
| `dpost_v2.infrastructure.storage.*` | Infrastructure | Implement filesystem/record storage adapters | Path/file operations and record store adapter behavior | Domain decision policy |
| `dpost_v2.infrastructure.sync.*` | Infrastructure | Implement sync adapters (`noop`, `kadi`) | Sync backend mapping and response normalization | Runtime composition policy |
| `dpost_v2.infrastructure.observability.*` | Infrastructure | Logging/metrics/tracing adapter ownership | Observability adapter behavior | Startup orchestration policy |
| `dpost_v2.infrastructure.runtime.ui.*` | Infrastructure | Headless/desktop UI adapter implementations | UI adapter behavior and mode-specific implementations | Runtime mode policy decisions |
| `dpost_v2.plugins.discovery` | Plugin infrastructure | Discover and normalize plugin descriptors | Namespace scanning and descriptor diagnostics | Runtime orchestration |
| `dpost_v2.plugins.host` | Plugin infrastructure | Register/activate plugins and provide lookup APIs | Plugin lifecycle and processor construction | Ingestion stage policy |
| `dpost_v2.plugins.profile_selection` | Plugin policy | Resolve runtime profile to plugin selections | Profile policy and selection constraints | Runtime dependency construction |

## Responsibility Rules

1. Application orchestrators call contracts, not concrete adapters by default.
2. Domain modules remain pure and side-effect free.
3. Infrastructure adapters may use external SDKs but do not define business
   policy.
4. Plugin modules expose contract-conformant exports and avoid global runtime
   wiring.
5. Ownership changes must update this catalog in the same change set.
