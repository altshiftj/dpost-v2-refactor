# Architecture Baseline (Current State)

## Snapshot Date

- 2026-03-05

## System Purpose

- Monitor local watch directories for instrument output.
- Route artifacts through device-specific processors.
- Persist local record state.
- Optionally synchronize records to external backends through adapter ports.

## Canonical Runtime Scope

- Command identity: `dpost`
- Runtime source of truth: `src/dpost_v2/`
- Active tests: `tests/dpost_v2/`
- Retired architecture modes: `v1`, `shadow`

## High-level Runtime Flow

1. Entrypoint (`dpost_v2.__main__`) normalizes startup request.
2. Startup bootstrap orchestrates settings/dependencies/context/composition.
3. Runtime composition builds validated port bindings and app bundle.
4. App loop handles events and dispatches ingestion flow.
5. Ingestion pipeline resolves, routes, persists, and emits outcomes.
6. Record/sync adapters persist local state and optionally publish remotely.

## Layer Intent

- Domain: pure business and data semantics.
- Application: orchestration, contracts, and use-case flow.
- Infrastructure: storage/sync/observability/UI adapters.
- Plugins: extension points, discovery, and host lifecycle.
- Runtime: dependency resolution and composition root.

## Current Key Components

Startup and composition:

- `src/dpost_v2/__main__.py`
- `src/dpost_v2/application/startup/bootstrap.py`
- `src/dpost_v2/application/startup/settings_service.py`
- `src/dpost_v2/application/startup/context.py`
- `src/dpost_v2/runtime/startup_dependencies.py`
- `src/dpost_v2/runtime/composition.py`

Application core:

- `src/dpost_v2/application/runtime/dpost_app.py`
- `src/dpost_v2/application/ingestion/engine.py`
- `src/dpost_v2/application/ingestion/runtime_services.py`
- `src/dpost_v2/application/records/service.py`
- `src/dpost_v2/application/contracts/ports.py`
- `src/dpost_v2/application/contracts/plugin_contracts.py`

Domain:

- `src/dpost_v2/domain/processing/`
- `src/dpost_v2/domain/naming/`
- `src/dpost_v2/domain/routing/rules.py`
- `src/dpost_v2/domain/records/local_record.py`

Infrastructure:

- `src/dpost_v2/infrastructure/storage/`
- `src/dpost_v2/infrastructure/sync/noop.py`
- `src/dpost_v2/infrastructure/sync/kadi.py`
- `src/dpost_v2/infrastructure/observability/`
- `src/dpost_v2/infrastructure/runtime/ui/`

Plugins:

- `src/dpost_v2/plugins/contracts.py`
- `src/dpost_v2/plugins/discovery.py`
- `src/dpost_v2/plugins/host.py`
- `src/dpost_v2/plugins/profile_selection.py`
- `src/dpost_v2/plugins/devices/`
- `src/dpost_v2/plugins/pcs/`

## Test Isolation Baseline

- Active CI and local quality gates target `tests/dpost_v2/`.
- Legacy pre-V2 test lanes are archived and not required for active V2 merge
  gates.
- Marker `legacy` remains reserved for archived compatibility suites.

## Notable Constraints

- `headless` remains default runtime UI mode.
- `desktop` mode remains supported and validated through runtime contracts.
- `noop` is default sync backend; `kadi` is optional and requires explicit
  backend configuration.
- Architecture and extension contracts are governed by:
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/extension-contracts.md`

## Governance Notes

- Migration-era plans/checklists/reports are retained for traceability but do
  not override current V2 architecture contracts.
- New structural changes should be captured in ADR updates under
  `docs/architecture/adr/`.
