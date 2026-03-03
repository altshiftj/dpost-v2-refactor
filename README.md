# dpost

`dpost` is a scientific data-ingestion watchdog for instrument workstations.
It monitors a local upload folder, routes artifacts to device-specific
processors, organizes output into record folders, persists local record state,
and optionally syncs records to Kadi.

The project is plugin-driven (`PC` plugins define active device sets; device
plugins define file selectors and processing behavior) and runs headless-first
with an optional desktop UI mode.

## Highlights

- Watches a configured folder for new files/folders (non-recursive).
- Resolves the correct device plugin using selector rules and optional file
  content probing.
- Waits for artifact stability before processing (with per-device overrides).
- Enforces filename prefix conventions and supports interactive rename flows.
- Organizes processed data into record folders and tracks upload state in a
  local JSON ledger.
- Supports best-effort immediate sync through a sync adapter port.
- Exposes Prometheus metrics and a small observability web app (`/health`,
  `/logs`).
- Supports headless and Tkinter desktop runtime modes.

## Project Status

- Canonical runtime identity: `dpost`
- Entry points:
  - `dpost` (console script)
  - `python -m dpost`
- Runtime posture: headless-first with optional desktop mode
- Sync adapter posture: adapter-based (`noop` default, optional `kadi`)

## Architecture At A Glance

The current codebase follows explicit ownership/layer boundaries:

- `src/dpost/domain/`: pure domain models and rules (naming, processing models,
  record entity behavior).
- `src/dpost/application/`: orchestration, ports, processing pipeline, records,
  config service, sessions.
- `src/dpost/infrastructure/`: UI/runtime adapters, logging, filesystem helpers,
  observability, sync adapters.
- `src/dpost/plugins/`: pluggy contracts, loader, profile selection.
- `src/dpost/runtime/`: startup composition and bootstrap.

More detail:

- `docs/architecture/README.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/architecture-baseline.md`
- `docs/architecture/extension-contracts.md`

## Governance

- License: `MIT` ([LICENSE](LICENSE))
- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## What dpost Does At Runtime

At startup, `dpost` composes a runtime context, loads a PC plugin and device
plugins, initializes directories, starts Prometheus metrics, optionally starts
the observability web server, and launches the UI/event loop.

During execution, the app:

1. Watches the configured upload directory with `watchdog`.
2. Queues create/modify events into an internal queue.
3. Runs a multi-stage processing pipeline:
   - device resolution (selectors + optional probes)
   - stability waiting / deferral / rejection
   - device-specific preprocessing
   - filename parsing and routing
   - rename flow (if needed)
   - record creation/update and persistence
   - immediate sync attempt (best effort)
4. Persists local record state to a JSON ledger for restart continuity.

## Built-in Plugins (In This Repository)

### PC plugins

These choose the active device plugin set for a workstation:

| PC plugin | Active device plugins |
|---|---|
| `eirich_blb` | `rmx_eirich_el1`, `rmx_eirich_r01` |
| `haake_blb` | `extr_haake` |
| `hioki_blb` | `erm_hioki` |
| `horiba_blb` | `psa_horiba`, `dsv_horiba` |
| `kinexus_blb` | `rhe_kinexus` |
| `tischrem_blb` | `sem_phenomxl2` |
| `zwick_blb` | `utm_zwick` |
| `test_pc` | `test_device` |

### Device plugins

These provide device config + file processor implementations:

| Device plugin | Typical inputs / selectors | Notes |
|---|---|---|
| `dsv_horiba` | `.wdb`, `.wdk`, `.wdp`, `.txt` | Horiba DSV files + exports |
| `erm_hioki` | `.csv`, `.xls`, `.xlsx` | Hioki export formats |
| `extr_haake` | `.xlsx` (allows `.xls`, `.xlsm`) | Haake export files |
| `psa_horiba` | `.ngb` + `.csv` | Sentinel/pairing flow, stages and zips native `.ngb` |
| `rhe_kinexus` | `.rdf` + `.csv` | Sentinel/pairing flow, stages and zips native `.rdf` |
| `rmx_eirich_el1` | `.txt` + filename pattern | `Eirich_EL1_TrendFile_*` |
| `rmx_eirich_r01` | `.txt` + filename pattern | `Eirich_R01_TrendFile_*` |
| `sem_phenomxl2` | image files + ELID folders | Handles SEM images and ELID exports |
| `utm_zwick` | `.zs2` + `.xlsx` | Zwick UTM native + export |
| `test_device` | `.tif`, `.txt` | Reference plugin for smoke tests and contracts |

## Installation

`dpost` is Windows-oriented (default paths use `C:\\Watchdog` and Desktop
folders, and the dependency set includes `pywin32`).

### Runtime install

```powershell
python -m pip install .
```

### Development install

```powershell
python -m pip install -e ".[dev]"
```

### Optional Kadi backend

```powershell
python -m pip install -e ".[kadi]"
```

You can combine extras as needed:

```powershell
python -m pip install -e ".[dev,kadi]"
```

## Quick Start (Safe Local Smoke Test)

This uses the built-in reference plugin profile (`test_pc` + `test_device`) and
the default no-op sync adapter so no external upload backend is touched.

```powershell
$env:DPOST_PLUGIN_PROFILE = "reference"
$env:DPOST_RUNTIME_MODE = "headless"   # default, explicit for clarity
$env:DPOST_SYNC_ADAPTER = "noop"       # default, explicit for clarity
python -m dpost
```

Notes:

- The process will run until stopped (`Ctrl+C`).
- Default paths are still created (see "Default Paths").
- Prometheus metrics start on port `8000` by default.
- The app has no CLI flags today; startup is configured via environment
  variables and plugins.

## Startup Configuration

`dpost` supports both canonical runtime selectors and bootstrap environment
variables.

### Runtime selectors

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `DPOST_RUNTIME_MODE` | `headless`, `desktop` | `headless` | Select UI/runtime mode |
| `DPOST_SYNC_ADAPTER` | `noop`, `kadi` | `noop` | Select sync adapter implementation |
| `DPOST_PLUGIN_PROFILE` | `reference` | unset | Use a predefined plugin profile (useful for smoke tests) |

### Startup settings (PC/devices/ports)

| Variable | Default | Purpose |
|---|---|---|
| `PC_NAME` | required (unless profile selected) | PC plugin identifier |
| `DEVICE_PLUGINS` | from PC plugin config | Comma/semicolon device override list |
| `PROMETHEUS_PORT` | `8000` | Prometheus metrics port |
| `OBSERVABILITY_PORT` | `8001` | Observability web app port |

`dpost` also supports prefixed override variables for the same values:

- `DPOST_PC_NAME`
- `DPOST_DEVICE_PLUGINS`
- `DPOST_PROMETHEUS_PORT`
- `DPOST_OBSERVABILITY_PORT`

These are resolved in the startup composition layer and override the non-prefixed
values when both are present.

### Logging environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DPOST_LOG_FILE_ENABLED` | enabled outside pytest | Enable/disable rotating file logging |
| `DPOST_LOG_FILE_PATH` | `C:\\Watchdog\\logs\\watchdog.log` | Override JSON log file path |
| `LOG_FILE_PATH` | same as above | Compatibility alias used by observability/logging |

### Bundled `.env` support

On startup, `dpost` attempts to load a bundled `.env` file when present. In a
non-frozen layout it checks `build/.env`; in a PyInstaller bundle it checks the
bundle directory.

## Default Paths

The default `PathSettings` (from `src/dpost/application/config/schema.py`)
create/use:

- `C:\\Watchdog\\` (app/log/persistence root)
- `C:\\Watchdog\\logs\\watchdog.log`
- `C:\\Watchdog\\record_persistence.json`
- `%USERPROFILE%\\Desktop\\Upload` (watch directory)
- `%USERPROFILE%\\Desktop\\Data` (record destination root)
- `%USERPROFILE%\\Desktop\\Data\\00_To_Rename`
- `%USERPROFILE%\\Desktop\\Data\\01_Exceptions`

## Filename Convention And Routing Behavior

The core naming policy expects a filename prefix shaped like:

`user-institute-sample`

Rules enforced by the domain naming policy include:

- `user`: letters only
- `institute`: letters only
- `sample`: letters/digits/underscore/space, max 30 chars

`dpost` sanitizes valid names (for example, spaces in `sample` become
underscores), prompts for rename in desktop mode, and can move canceled/invalid
items to the rename bucket.

## Runtime Modes

### `headless` (default)

- Uses `HeadlessRuntimeUI`
- Suppresses dialogs
- Auto-approves append-record prompts
- Runs an in-process scheduler/event loop
- Good for tests, smoke runs, and service-style execution

### `desktop`

- Uses `TKinterRuntimeUI`
- Shows rename/info/error dialogs
- Presents session "Done" prompt
- Preserves interactive workstation behavior

## Sync Adapters

### `noop` (default)

- Implements the sync port and intentionally performs no backend operations.
- Recommended for local development and CI.

### `kadi` (optional)

- Enabled by selecting `DPOST_SYNC_ADAPTER=kadi` and installing optional Kadi
  dependencies (`.[kadi]`).
- Wraps `KadiSyncManager` behind the `SyncAdapterPort`.
- Immediate sync remains best effort; failures are surfaced and local data is
  preserved for later retries.

## Observability And Metrics

`dpost` starts a Prometheus metrics endpoint on startup:

- `http://localhost:8000/metrics` (default)

Metrics include:

- `files_processed`
- `files_processed_by_record`
- `files_failed`
- `events_processed`
- `file_process_time_seconds`
- `session_exit_status`
- `session_duration_seconds`
- `exceptions_thrown`

The observability server (Flask + Waitress) exposes:

- `http://localhost:8001/health`
- `http://localhost:8001/logs`

`/logs` supports a `tail` query parameter (for example `?tail=200`) and renders
JSON logs in a simple browser viewer with client-side filtering.

## Extending dpost

`dpost` uses `pluggy` with the canonical hook namespace `dpost`.

### Plugin loading contract

- Hook namespace: `dpost`
- Device plugin entry-point group: `dpost.device_plugins`
- PC plugin entry-point group: `dpost.pc_plugins`
- In-repo plugin package locations:
  - `src/dpost/device_plugins/<plugin_name>/`
  - `src/dpost/pc_plugins/<plugin_name>/`

### Device plugin contract (minimum)

Device plugin factories must provide:

- `get_config()`
- `get_file_processor()`

The processor should implement `FileProcessorABS` and must implement:

- `device_specific_processing(...)`

Optional but important hooks include:

- `device_specific_preprocessing(...)`
- `probe_file(...)`
- `matches_file(...)`
- `should_queue_modified(...)`
- `configure_runtime_context(...)`

Minimal registration example:

```python
from dpost.plugins.system import hookimpl


class MyDevicePlugin:
    def get_config(self):
        ...

    def get_file_processor(self):
        ...


@hookimpl
def register_device_plugins(registry):
    registry.register("my_device", MyDevicePlugin)
```

### PC plugin contract (minimum)

PC plugin factories must provide:

- `get_config()` returning a `PCConfig`-compatible object

`PCConfig.active_device_plugins` defines which device plugin IDs are active for
that workstation.

### Sync adapter contract

Implement `dpost.application.ports.sync.SyncAdapterPort`:

- `sync_record_to_database(local_record) -> bool`

Wire adapter selection in `src/dpost/runtime/composition.py`.

## Development

### Run locally

Reference profile + no-op sync:

```powershell
$env:DPOST_PLUGIN_PROFILE = "reference"
$env:DPOST_RUNTIME_MODE = "headless"
$env:DPOST_SYNC_ADAPTER = "noop"
python -m dpost
```

Example workstation startup (desktop UI + Kadi):

```powershell
$env:PC_NAME = "horiba_blb"
$env:DPOST_RUNTIME_MODE = "desktop"
$env:DPOST_SYNC_ADAPTER = "kadi"
python -m dpost
```

### Quality gates

```powershell
python -m ruff check .
python -m black --check .
python -m pytest -m legacy
python -m pytest
```

## Documentation

- `USER_README.md`: operator-focused runtime usage guide
- `DEVELOPER_README.md`: contributor/developer guide
- `docs/architecture/README.md`: architecture documentation index

## Contributing

Contributions are easiest to review when they preserve behavior, keep changes
bounded by ownership/layer boundaries, and include targeted tests for changed
logic.

If you are adding plugins or refactoring architecture-heavy modules, also
review:

- `docs/architecture/architecture-contract.md`
- `docs/architecture/extension-contracts.md`
- `docs/architecture/responsibility-catalog.md`

## License

This repository currently does not include a top-level `LICENSE` file. Add one
before publishing or accepting external open-source contributions under a
specific license.
