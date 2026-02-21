# dpost Developer Guide

## Architecture Overview
`dpost` is the canonical runtime identity. The architecture follows explicit
layer boundaries:

- `src/dpost/domain/`: pure domain rules and data models.
- `src/dpost/application/`: orchestration, ports, processing, records, session.
- `src/dpost/infrastructure/`: runtime/UI/logging/storage/sync adapters.
- `src/dpost/plugins/`: plugin loader, contracts, profile selection boundaries.
- `src/dpost/runtime/`: composition root and runtime bootstrap entry surfaces.

Canonical dependency and ownership rules live in:
- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`
- `docs/architecture/extension-contracts.md`

## Startup Flow and Environment
1. `python -m dpost` enters `src/dpost/__main__.py`.
2. Startup composes dependencies through `src/dpost/runtime/composition.py`.
3. Runtime bootstrap executes via `src/dpost/runtime/bootstrap.py`.

Key environment variables:
- `PC_NAME` (required): active PC plugin identifier.
- `DEVICE_PLUGINS` (optional): comma/semicolon override list for active devices.
- `DPOST_RUNTIME_MODE` (optional): `headless` (default) or `desktop`.
- `DPOST_SYNC_ADAPTER` (optional): `noop` (default) or `kadi`.
- `PROMETHEUS_PORT` and `OBSERVABILITY_PORT` (optional): observability ports.

## Plugin System (Canonical)
Canonical plugin loading is owned by:
- `src/dpost/plugins/system.py`
- `src/dpost/plugins/loading.py`
- `src/dpost/plugins/contracts.py`

Canonical plugin namespace contract:
- hook namespace: `dpost`
- device group: `dpost.device_plugins`
- PC group: `dpost.pc_plugins`

In-repo canonical plugin packages:
- `src/dpost/device_plugins/<plugin_name>/`
- `src/dpost/pc_plugins/<plugin_name>/`

Legacy namespace/hook fallback is retired from canonical `src/dpost/**` paths.

## Processing, Records, and Sync
- Processing orchestration:
  - `src/dpost/application/processing/file_process_manager.py`
- Record lifecycle:
  - `src/dpost/application/records/record_manager.py`
- Sync port and adapters:
  - `src/dpost/application/ports/sync.py`
  - `src/dpost/infrastructure/sync/noop.py`
  - `src/dpost/infrastructure/sync/kadi.py`

Immediate-sync policy remains best-effort and now surfaces actionable user
errors through dpost interaction messages when sync fails.

## Extending dpost
### Add a Device Plugin
1. Create `src/dpost/device_plugins/<name>/` with:
   - `settings.py`
   - `file_processor.py`
   - `plugin.py`
2. In `plugin.py`, register with `@hookimpl` from `dpost.plugins.system`.
3. Factory contract must provide:
   - `get_config()`
   - `get_file_processor()`
4. Ensure processor implements required `FileProcessorABS` behavior.
5. Add focused unit/integration tests for probe/preprocess/process behavior.

### Add a PC Plugin
1. Create `src/dpost/pc_plugins/<name>/` with:
   - `settings.py`
   - `plugin.py`
2. Register with `@hookimpl` in `plugin.py`.
3. Return a `PCConfig` with `active_device_plugins` populated.
4. Add tests covering plugin configuration and loader behavior.

### Add a Sync Adapter
1. Implement adapter against `SyncAdapterPort` in `src/dpost/infrastructure/sync/`.
2. Wire selection in `src/dpost/runtime/composition.py`.
3. Add migration tests for adapter selection and startup failure messaging.

## Local Development
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
```

Run app:
```powershell
$env:PC_NAME = "test_pc"
$env:DEVICE_PLUGINS = "test_device"
python -m dpost
```

## Quality Gates
Run from repository root:
```powershell
python -m ruff check .
python -m black --check .
python -m pytest -m migration
python -m pytest -m legacy
python -m pytest
```

Marker intent:
- `migration`: canonical dpost migration/cutover contracts.
- `legacy`: archived compatibility characterization contracts.

## Migration and Architecture Docs
- Phase 9-13 closure PR package:
  - `docs/reports/20260221-phase9-13-closure-pr-package.md`
- Part 3 extraction closure docs:
  - `docs/planning/archive/20260221-part3-domain-layer-extraction-roadmap.md`
  - `docs/checklists/archive/20260221-part3-domain-layer-extraction-checklist.md`
  - `docs/reports/archive/20260221-part3-domain-layer-extraction-inventory.md`
- Full legacy retirement closure docs:
  - `docs/reports/archive/20260221-full-legacy-repo-retirement-inventory.md`
  - `docs/reports/archive/20260221-full-legacy-retirement-migration-notes.md`
  - `docs/planning/archive/20260221-full-legacy-repo-retirement-roadmap.md`
  - `docs/checklists/archive/20260221-full-legacy-repo-retirement-checklist.md`
  - `docs/checklists/archive/20260221-final-manual-validation-runbook.md`
- Historical migration docs:
  - `docs/reports/archive/`
  - `docs/planning/archive/`
  - `docs/checklists/archive/`
- Architecture ADRs:
  - `docs/architecture/adr/`
