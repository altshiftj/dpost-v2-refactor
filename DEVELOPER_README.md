# dpost Developer Guide

## Architecture Overview
`dpost` remains the command name, and V2 runtime ownership is under
`src/dpost_v2/`.

Layer boundaries:

- `src/dpost_v2/domain/`: pure rules/models.
- `src/dpost_v2/application/`: startup + ingestion + runtime/session + contracts.
- `src/dpost_v2/infrastructure/`: storage/sync/observability/runtime adapters.
- `src/dpost_v2/plugins/`: plugin contracts/discovery/host and namespaces.
- `src/dpost_v2/runtime/`: composition and dependency wiring.

Canonical architecture docs:

- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`
- `docs/architecture/extension-contracts.md`

## Startup Flow

1. `dpost` dispatches to `dpost_v2.__main__.main`.
2. Startup orchestration runs in `src/dpost_v2/application/startup/bootstrap.py`.
3. Runtime dependencies resolve via `src/dpost_v2/runtime/startup_dependencies.py`.
4. Runtime composition executes via `src/dpost_v2/runtime/composition.py`.

## Runtime Modes

Active runtime UI modes:

- `headless` (default)
- `desktop`

Retired architecture modes:

- `v1`
- `shadow`

## Plugin System

Plugin namespaces:

- Device plugins: `src/dpost_v2/plugins/devices/<name>/`
- PC plugins: `src/dpost_v2/plugins/pcs/<name>/`

Discovery/host modules:

- `src/dpost_v2/plugins/discovery.py`
- `src/dpost_v2/plugins/host.py`
- `src/dpost_v2/plugins/contracts.py`

Plugin contracts:

- `src/dpost_v2/application/contracts/plugin_contracts.py`

Device plugin required exports:

- `metadata()`
- `capabilities()`
- `validate_settings(raw_settings)`
- `create_processor(settings)`

PC plugin required exports:

- `metadata()`
- `capabilities()`
- `create_sync_adapter(settings)`
- `prepare_sync_payload(record, context)`

## Ingestion, Records, Sync

- Ingestion engine: `src/dpost_v2/application/ingestion/engine.py`
- Runtime services: `src/dpost_v2/application/ingestion/runtime_services.py`
- Record service: `src/dpost_v2/application/records/service.py`
- Sync contract: `dpost_v2.application.contracts.ports.SyncPort`
- Sync adapters:
  - `src/dpost_v2/infrastructure/sync/noop.py`
  - `src/dpost_v2/infrastructure/sync/kadi.py`

## Local Development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
```

Run runtime:

```powershell
$env:DPOST_PLUGIN_PROFILE = "reference"
$env:DPOST_RUNTIME_MODE = "headless"
$env:DPOST_SYNC_ADAPTER = "noop"
dpost
```

## Quality Gates

```powershell
python -m ruff check src/dpost_v2 tests/dpost_v2
python -m black --check src/dpost_v2 tests/dpost_v2
python -m pytest -q tests/dpost_v2
```

CI-equivalent subsets:

```powershell
python -m pytest -q tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/smoke
python -m pytest -q tests/dpost_v2/application/startup/test_bootstrap.py tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py
```

## Notes

- Legacy pre-V2 test lanes are archived and not part of active V2 gates.
- Migration-era planning/pseudocode artifacts are historical references unless
  explicitly marked active.
