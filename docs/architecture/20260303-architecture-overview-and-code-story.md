# Architecture Overview and Code Story

## Date

- 2026-03-05 (V2-only refresh)

## What This System Is

- `dpost` is a plugin-driven watchdog runtime for scientific data ingestion.
- It watches filesystem drop zones, routes artifacts to plugin processors,
  persists record state, and can sync through pluggable adapters.

## Structural Shape

1. Domain layer (`src/dpost_v2/domain/`)
- Pure models and policy logic.
- No runtime wiring or adapter side effects.

2. Application layer (`src/dpost_v2/application/`)
- Startup orchestration, ingestion flow, runtime/session coordination,
  contracts.

3. Infrastructure layer (`src/dpost_v2/infrastructure/`)
- Concrete adapters for storage, sync, observability, and runtime UI.

4. Plugin layer (`src/dpost_v2/plugins/`)
- Contract-aware plugin discovery, host lifecycle, profile selection, and
  plugin namespaces.

5. Runtime layer (`src/dpost_v2/runtime/`)
- Startup dependency resolution and composition root.

## Runtime Story (Startup to Running Loop)

1. Entrypoint normalizes request:
- `src/dpost_v2/__main__.py`

2. Startup bootstrap orchestrates settings/dependencies/context/composition:
- `src/dpost_v2/application/startup/bootstrap.py`

3. Dependencies and adapter factories are resolved:
- `src/dpost_v2/runtime/startup_dependencies.py`

4. Composition validates port bindings and builds runnable app:
- `src/dpost_v2/runtime/composition.py`

5. Runtime app coordinates lifecycle and ingestion dispatch:
- `src/dpost_v2/application/runtime/dpost_app.py`

## Processing Story (Per Artifact)

1. Ingestion engine runs deterministic stage flow:
- `src/dpost_v2/application/ingestion/engine.py`

2. Runtime services expose side-effect collaborators to ingestion flow:
- `src/dpost_v2/application/ingestion/runtime_services.py`

3. Domain rules keep naming/routing/processing decisions pure:
- `src/dpost_v2/domain/naming/`
- `src/dpost_v2/domain/routing/rules.py`
- `src/dpost_v2/domain/processing/`

## Plugin Story

- Discovery and descriptor normalization:
  - `src/dpost_v2/plugins/discovery.py`
- Registry/activation host:
  - `src/dpost_v2/plugins/host.py`
- Profile-driven selection:
  - `src/dpost_v2/plugins/profile_selection.py`
- Plugin namespaces:
  - `src/dpost_v2/plugins/devices/`
  - `src/dpost_v2/plugins/pcs/`

## Records and Sync Story

- Record lifecycle service:
  - `src/dpost_v2/application/records/service.py`
- Storage adapters:
  - `src/dpost_v2/infrastructure/storage/`
- Sync contracts and adapters:
  - `src/dpost_v2/application/contracts/ports.py`
  - `src/dpost_v2/infrastructure/sync/noop.py`
  - `src/dpost_v2/infrastructure/sync/kadi.py`

## Governance Story

- Baseline/contract/responsibility docs are maintained under
  `docs/architecture/`.
- Active CI and local quality gates target V2 paths only.
- Legacy architecture modes (`v1`, `shadow`) and legacy test lanes are retired
  from active runbooks.
