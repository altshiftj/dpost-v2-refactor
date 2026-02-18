# Architecture Baseline (Current State)

## Snapshot Date
- 2026-02-18

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
- `src/ipat_watchdog/core/app/bootstrap.py`
- New migration composition scaffold:
- `src/dpost/runtime/composition.py`
- dpost composition now validates selected sync adapter and injects a
  `sync_manager_factory` into legacy bootstrap wiring.
- dpost sync adapter port contract:
- `src/dpost/application/ports/sync.py`
- dpost reference sync adapter (noop):
- `src/dpost/infrastructure/sync/noop.py`
- Runtime loop and event handling:
- `src/ipat_watchdog/core/app/device_watchdog_app.py`
- Processing orchestration:
- `src/ipat_watchdog/core/processing/file_process_manager.py`
- Plugin loading and registration:
- `src/ipat_watchdog/plugin_system.py`
- Configuration schema and runtime service:
- `src/ipat_watchdog/core/config/`
- Local record persistence:
- `src/ipat_watchdog/core/records/`
- Current Kadi backend implementation:
- `src/ipat_watchdog/core/sync/sync_kadi.py`

## Current Test Isolation Baseline
- Pytest markers enforce split test intent:
- `legacy` marker for current `ipat_watchdog` behavior contract tests.
- `migration` marker for `dpost` migration and cutover tests.
- New migration entrypoint tests currently live in:
- `tests/migration/test_dpost_main.py`
- Phase 3 sync adapter selection tests currently live in:
- `tests/migration/test_sync_adapter_selection.py`

## Notable Constraints in Current Baseline
- Some global/singleton patterns are still present in runtime wiring.
- Legacy constant fallbacks coexist with config service access.
- Desktop UI is a default runtime path today.
- Sync backend is currently Kadi-coupled in core paths.
- dpost composition still delegates full runtime bootstrap to legacy wiring while
  sync adapter kernel contracts are being introduced incrementally.

## Migration Notes
- Headless-first migration is the current execution posture.
- Framework-first sequencing is active: kernel and contracts are prioritized before concrete integrations.
- Sync is being moved toward optional adapter architecture for multi-ELN/database support.
- Major structural updates should be tracked via ADRs in `docs/architecture/adr/`.
