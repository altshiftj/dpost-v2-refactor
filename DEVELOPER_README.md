# IPAT Data Watchdog - Developer Guide

## Architecture Overview
IPAT Data Watchdog monitors the workstation upload folder, normalises new artefacts through device-specific processors, persists them into structured record directories, and synchronises the resulting records with the Kadi database. The codebase is organised around a compact core with pluggable extensions:

- `src/ipat_watchdog/core/app/device_watchdog_app.py` contains `DeviceWatchdogApp`, which coordinates file-system monitoring, processing, and UI glue.
- `watchdog` observers capture filesystem events, enqueue them, and the Tkinter UI loop drains the queue so processing always runs on the UI thread.
- `ConfigService` (`core/config/service.py`) exposes active PC/device configuration and scopes overrides via context managers.
- `FileProcessManager` (`core/processing/file_process_manager.py`) performs validation, routing, rename flows, record construction, and sync hand-off.
- `RecordManager` plus `core/sync/sync_kadi.KadiSyncManager` persist record state to disk and mirror artefacts into Kadi via `kadi_apy`.
- UI abstractions (`core/ui/adapters.py`) bridge domain prompts onto the concrete Tkinter implementation (`core/ui/ui_tkinter.py`).

## Startup Flow and Environment
1. `src/dpost/__main__.py` invokes `compose_bootstrap()` in
   `src/dpost/runtime/composition.py`.
2. `collect_startup_settings()` optionally loads a bundled `.env` from `build/.env`; real environment variables always win.
3. Environment variables:
   - `PC_NAME` (**required**) – selects the PC plugin.
   - `DEVICE_PLUGINS` (optional) – comma/semicolon list overriding the PC plugin’s device list.
   - `PROMETHEUS_PORT`, `OBSERVABILITY_PORT` (optional) – integer overrides for telemetry endpoints.
4. Bootstrap loads the PC plugin, instantiates the referenced device plugins, initialises `ConfigService`, and ensures all required directories exist via `core/storage/filesystem_utils.init_dirs()`.
5. Background services:
   - Prometheus metrics server (`metrics.py`) on `PROMETHEUS_PORT` (default `8000`).
   - Observability server (`observability.py`) on `OBSERVABILITY_PORT` (default `8001`) when Flask/Waitress are importable; a warning is logged otherwise.
6. `DeviceWatchdogApp` starts the `watchdog` observer, registers UI handlers, and enters the Tk main loop via `DeviceWatchdogApp.run()`.

## Filesystem Layout and Naming
Defaults come from `core/config/schema.PathSettings`:

- Application data: `C:\Watchdog\` (also holds `record_persistence.json` and logs).
- Watch directory: `Desktop\Upload\`.
- Records root: `Desktop\Data\`.
- Invalid naming bucket: `Desktop\Data\00_To_Rename\`.
- Processing failures: `Desktop\Data\01_Exceptions\`.

`ConfigService.current` exposes an `ActiveConfig` with these paths. Record folders are created as `Data/<INSTITUTE>/<USER>/<DEVICE?-SAMPLE>` (institute/user uppercased, device abbreviation prefixed when known). `record_persistence.json` carries record metadata across restarts.

Filename validation in `core/storage/filesystem_utils` enforces the `user-institute-sample` pattern. `NamingSettings` allows device-specific overrides, but the bundled plugins rely on the defaults (letters for user/institute, 30-character sample limit, underscores/spaces allowed in the sample segment).

## Plugin System
`plugin_system.py` uses Pluggy to register and load PC/device plugins on demand. Registrations are provided by each plugin module via `@hookimpl`, and entry points declared in `pyproject.toml` make them discoverable when installed.

Bundled device plugins:
- `sem_phenomxl2` – Thermo Phenom XL2 SEM
- `psa_horiba` – Horiba PSA
- `dsv_horiba` – Horiba DSV
- `utm_zwick` – Zwick universal testing machine
- `extr_haake` – Haake twin-screw extruder
- `rhe_kinexus` – Kinexus rheometer
- `test_device` – test doubles used in automated suites

Bundled PC plugins:
- `tischrem_blb` – activates `sem_phenomxl2`
- `horiba_blb` – activates `psa_horiba`, `dsv_horiba`
- `zwick_blb` – activates `utm_zwick`
- `haake_blb` – activates `extr_haake`
- `kinexus_blb` – activates `rhe_kinexus`
- `test_pc` – activates `test_device` with overrideable paths for tests

`loader.get_devices_for_pc(pc_name)` reads `PCConfig.active_device_plugins`. PC plugins typically cache their `PCConfig` instance returned from local `build_config()` helpers.

## Processing Pipeline
`FileProcessManager` orchestrates the following stages:

1. `DeviceWatchdogApp.QueueingEventHandler` queues `on_created` events from `watchdog`.
2. The Tk scheduler calls `process_events()` every 100 ms, draining a single queue item to keep the UI responsive.
3. Internal staging artefacts (paths ending with `.__staged__`) are ignored.
4. Device resolution combines selector rules (`DeviceConfig.files`) with lightweight processor probes (`FileProcessorABS.probe_file`).
5. `FileStabilityTracker` waits for items to stop changing, using device-specific `WatcherSettings`.
6. Filename validation either proceeds, invokes the rename dialog (`RenameService`), or moves the item to `00_To_Rename`.
7. Records are created/reused via `RecordManager`; IDs derive from device metadata (`DeviceMetadata`) and the filename prefix.
8. Device processors (`device_plugins/*/file_processor.py`) move or transform artefacts into record folders and return `ProcessingOutput`.
9. Metrics are updated and success notifications displayed; rejected items increment failure counters and are moved to `01_Exceptions`.
10. Records are persisted to disk and, with `immediate_sync=True`, marked for upload to Kadi.

### Preprocessing/Processing Contract
- `FileProcessorABS.device_specific_preprocessing` returns `None` to defer (waiting for paired artefacts) or a `PreprocessingResult` to continue the pipeline.
- `PreprocessingResult.effective_path` is the path used for prefix/extension parsing; use `PreprocessingResult.passthrough(...)` when no staging or overrides are required.
- Use `PreprocessingResult.with_prefix(...)` or `PreprocessingResult.with_extension(...)` when preprocessing needs to override the parsed filename components.
- `device_specific_processing` receives the resolved `file_id` and `extension` and must return a `ProcessingOutput` describing the final path and datatype.

## Logging, Observability, and Metrics
- Logging (`core/logging/logger.py`) writes JSON lines to `C:\Watchdog\logs\watchdog.log` with a rotating file handler plus stdout mirroring.
- Metrics (`metrics.py`) expose `files_processed`, `files_processed_by_record`, `files_failed`, `events_processed`, `file_process_time_seconds`, `exceptions_thrown`, `session_exit_status`, and `session_duration_seconds`.
- `observability.py` serves `GET /health` and `GET /logs?tail=N`, providing a minimal log viewer. Missing Flask/Waitress simply disables the endpoint; the rest of the app continues to run.

## Kadi Synchronisation
`core/sync/sync_kadi.KadiSyncManager` leverages `kadi_apy` to mirror `LocalRecord` artefacts into Kadi. It prepares per-user and per-device collections/groups, uploads new artefacts, and marks records as uploaded. Failures are logged and surfaced via the UI; processing continues so long as other components remain healthy. Ensure runtime credentials consumable by `kadi_apy` (service tokens, config files, etc.) are present.

## Local Development
```powershell
# From the repository root
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]

# Environment
$env:PC_NAME = "test_pc"                # or a production PC plugin
$env:DEVICE_PLUGINS = "test_device"     # optional override

python -m dpost
```

The console script `dpost` is also registered when the project is installed.
Metrics are served at `http://localhost:8000/metrics`; if the observability
extras are installed, the log viewer lives at `http://localhost:8001/logs`.

Run tests with:
```powershell
python -m pip install -e .[ci]
pytest
```
The suite mixes unit and integration coverage and relies on Pyfakefs for filesystem isolation.

## Extending the System
### Adding a Device Plugin
1. Create `src/ipat_watchdog/device_plugins/my_device/` with `__init__.py`, `settings.py`, `file_processor.py`, and `plugin.py`.
2. `settings.py` must return a fully-populated `DeviceConfig`.
3. Implement `FileProcessorABS` hooks for preprocessing, probing, and processing.
4. Register the plugin via `@hookimpl` and add an entry under `[project.entry-points."ipat_watchdog.device_plugins"]` in `pyproject.toml`.
5. Wire up optional extras if the plugin needs additional dependencies.

### Adding a PC Plugin
1. Create `src/ipat_watchdog/pc_plugins/my_pc/` with `settings.py` returning a `PCConfig` and `plugin.py` implementing `PCPlugin`.
2. Set `PCConfig.active_device_plugins` to the identifiers the workstation should activate.
3. Override `PathSettings`, `NamingSettings`, or `WatcherSettings` if the workstation layout differs from the defaults.
4. Register the entry point under `[project.entry-points."ipat_watchdog.pc_plugins"]`.

## Troubleshooting
- **“PC_NAME must be provided”** – ensure the environment variable is set before launching the app.
- **No device plugins resolved** – update the PC plugin’s `active_device_plugins` or set `DEVICE_PLUGINS`.
- **Observability server missing** – install Flask and Waitress (see optional extras) or ignore if not needed.
- **Files lingering in Upload** – inspect `C:\Watchdog\logs\watchdog.log`; invalid names are redirected to `00_To_Rename`, processing errors go to `01_Exceptions`.
- **Kadi sync failures** – verify `kadi_apy` credentials and network reachability; failed uploads leave records marked unsynchronised but do not stop the watcher.

For user-focused instructions see `USER_README.md`. PC plugin authors should also consult `PC_PLUGIN_README.md`.

## Cutover Notes
- Canonical project/package identity is `dpost`.
- See `docs/reports/20260219-phase8-cutover-migration-notes.md` for transition
  command mapping, contributor expectations, and legacy sunset information.
