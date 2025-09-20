# IPAT Data Watchdog – Developer Documentation

## 🏗️ Architecture Overview

IPAT Data Watchdog is a modular, plugin-based scientific data ingestion system designed to monitor directories for incoming files from laboratory devices, process them according to device-specific rules, and synchronize the data to external databases. The application follows a clean architecture pattern with clear separation of concerns.

### Core Design Principles

- **Plugin Architecture**: Device-specific logic is encapsulated in plugins  
- **Event-Driven**: Uses filesystem events and queues for responsive processing  
- **Configurable**: Settings are externalized and device-specific  
- **Observable**: Built-in metrics, logging, and health monitoring  
- **Testable**: Dependency injection and abstract interfaces throughout  

---

# Developer Guide (Ground Truth)

This guide reflects what’s actually implemented in the codebase today. It maps the real modules, runtime behavior, plugin system, processing pipeline, metrics, and tests.

## What It Does

The app watches a directory for new files/folders from laboratory devices, validates and routes them via device-specific processors, organizes them into a record structure, and syncs records to an external system. It exposes Prometheus metrics and an observability web UI, and logs structured JSON to disk.

## Runtime and Entry Point

- **Entry point**: `src/ipat_watchdog/__main__.py` defines `main()` and is also registered as a console script `ipat-watchdog`.  
- **Env loading**: on startup it loads a bundled `.env` from `build/.env` (when present). This mirrors the frozen app layout. You can still set environment variables in the OS; bundled values don’t override existing ones.  
- **Required env**: `PC_NAME` must be set or the app exits; a fallback default of `tischrem_blb` is applied if missing.  
- **Device list**: optional `DEVICE_PLUGINS` (comma/semicolon allowed) overrides device auto-selection. If not set, devices are inferred from the loaded PC plugin via `loader.get_devices_for_pc()`.  
- **Services started**:
  - Prometheus metrics server on port `8000`  
  - Observability server on port `8001` (Flask + Waitress)  

---

## Plugins

Plugins are discovered via Python entry points (`pyproject.toml`) and loaded with `importlib.metadata.entry_points`.

- **Device plugins**:
  - `sem_phenomxl2` → `SEMPhenomXL2Plugin`  
  - `utm_zwick` → `UTMZwickPlugin`  
  - `psa_horiba` → `PSAHoribaPlugin`  
  - `dsv_horiba` → `DSVHoribaPlugin`  
  - `test_device` → `TestDevicePlugin`  

- **PC plugins**:
  - `tischrem_blb` → `PCTischREMPlugin`  
  - `zwick_blb` → `PCZwickPlugin`  
  - `horiba_blb` → `PCHoribaPlugin`  
  - `test_pc` → `TestPCPlugin`  

Each device plugin implements:

- `DevicePlugin.get_config() -> DeviceConfig`  
- `DevicePlugin.get_file_processor() -> FileProcessorABS`  

Each PC plugin implements:

- `PCPlugin.get_config() -> PCConfig`  

---

## Configuration Model

`core/config` provides runtime configuration helpers:

- `ConfigService(pc: PCConfig, devices: Iterable[DeviceConfig])` registers configs.  
- Device activation is scoped via `ConfigService.activate_device(device)` context manager.  
- `ActiveConfig` exposes effective paths, naming, watcher, and device metadata.  

---

## Logging and Observability

- **Logging**: JSON logs at `C:/Watchdog/logs/watchdog.log` with rotation. Logs also go to stdout.  
- **Observability** (from `observability.py`):
  - `GET /health` → `{"status": "ok"}`  
  - `GET /logs?tail=N` → HTML log viewer with filtering  
  - Defaults to `C:/Watchdog/logs/watchdog.log`  
  - Served by Waitress on `0.0.0.0:8001`  

---

## Metrics (Prometheus)

Exposed on port `8000` (`metrics.py`):

- `files_processed` (Counter)  
- `files_processed_by_record{record_id=...}` (Counter)  
- `files_failed` (Counter)  
- `events_processed` (Counter)  
- `file_process_time_seconds` (Histogram)  
- `session_exit_status` (Gauge; 0=clean, 1=crashed)  
- `session_duration_seconds` (Gauge)  
- `exceptions_thrown` (Counter)  

---

## File Watching and UI

- **File watching**: `DeviceWatchdogApp` uses `watchdog` to observe directories.  
- **UI**: Tkinter (`core/ui/ui_tkinter.py`) for dialogs, warnings, prompts. Event loop runs via `UiTaskScheduler`.  

---

## Processing Pipeline

Steps (from `core/processing/file_process_manager.py`):

1. Ignore internal staging artefacts (`.__staged__`).  
2. Resolve device (`DeviceResolver` + `FileProcessorABS.probe_file`).  
3. Check file stability (`FileStabilityTracker.wait()`).  
4. Device-specific preprocessing (`device_specific_preprocessing`).  
5. Parse filename and determine routing.  
6. Handle rename flow if needed.  
7. Process and add to record (`device_specific_processing`).  

## Running Locally (Windows PowerShell)

```powershell
# From repo root
python -m pip install -e .[dev]

# Minimal env
$env:PC_NAME = "tischrem_blb"
# optional: $env:DEVICE_PLUGINS = "sem_phenomxl2"

# Run
python -m ipat_watchdog
# or
ipat-watchdog
```

- Prometheus: http://localhost:8000/metrics  
- Observability: http://localhost:8001/logs and http://localhost:8001/health  

---

## Tests (pytest)

- CI/test extras include `pytest` and `pyfakefs`.  
- Test helpers live under `tests/helpers`.  
- Both unit and integration tests exist.  

```powershell
python -m pip install -e .[ci]
pytest
```

---

## Extending the System

### Add a Device Plugin

1. Create `src/ipat_watchdog/device_plugins/my_device/` with `plugin.py`, `settings.py`, `file_processor.py`.  
2. Register under `[project.entry-points."ipat_watchdog.device_plugins"]`.  
3. Add an optional dependency in `pyproject.toml`.  

### Add a PC Plugin

1. Create `src/ipat_watchdog/pc_plugins/my_pc/` with `plugin.py` and `settings.py`.  
2. Register under `[project.entry-points."ipat_watchdog.pc_plugins"]`.  
3. Set `PC_NAME=my_pc`.  

---

## Deployment

### Development

```bash
git clone <repository-url>
cd ipat_data_watchdog
pip install -e .[dev]
cp .env.example .env
python -m ipat_watchdog
```

### Production

```bash
pip install ipat-watchdog[tischrem_blb]
export PC_NAME=tischrem_blb
pyinstaller --onefile --name wd_tischrem_blb src/ipat_watchdog/__main__.py
```

---

## Contributing Guidelines

- Follow PEP 8  
- Use type hints  
- Add docstrings  
- Keep >80% test coverage  

### Development Tools

```bash
black src/ tests/
mypy src/
ruff check src/ tests/
pytest --cov=ipat_watchdog
```

---

## Troubleshooting

- **Plugin Not Found**: check `PC_NAME`, entry points, `pip list`.  
- **File Processing Errors**: check permissions, directory structure, logs.  
- **Database Sync Failures**: check credentials, API status, network.  
- **UI Issues**: verify display environment, check logs.  

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export PC_NAME=tischrem_blb
python -m ipat_watchdog
```

---

## 📚 Additional Resources

- Watchdog Library: https://python-watchdog.readthedocs.io/  
- Kadi API: https://kadi.readthedocs.io/  
- Prometheus Client: https://prometheus.github.io/client_python/  
- PyInstaller: https://pyinstaller.readthedocs.io/  

---

For user-focused docs, see `USER_README.md`.  
For deployment guides, see `docs/`.
