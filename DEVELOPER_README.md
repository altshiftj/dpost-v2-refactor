# IPAT Data Watchdog - Developer Documentation

## 🏗️ Architecture Overview

IPAT Data Watchdog is a modular, plugin-based scientific data ingestion system designed to monitor directories for incoming files from laboratory devices, process them according to device-specific rules, and synchronize the data to external databases. The application attempts to follow a clean architecture pattern with clear separation of concerns.

### Core Design Principles

- **Plugin Architecture**: Device-specific logic is encapsulated in plugins
- **Event-Driven**: Uses filesystem events and queues for responsive processing
- **Configurable**: Settings are externalized and device-specific
- **Observable**: Built-in metrics, logging, and health monitoring
- **Testable**: Dependency injection and abstract interfaces throughout

## 📁 Project Structure

```
src/ipat_watchdog/
├── __main__.py                    # Application entry point
├── loader.py                      # Plugin discovery and loading
├── metrics.py                     # Prometheus metrics definitions
├── observability.py              # Health checks and log viewer
├── core/                          # Core framework components
│   ├── app/
# IPAT Data Watchdog — Developer Guide (ground truth)

This guide reflects what’s actually implemented in the codebase today. It maps the real modules, runtime behavior, plugin system, processing pipeline, metrics, and tests.

## What it does

The app watches a directory for new files/folders from laboratory devices, validates and routes them via device-specific processors, organizes them into a record structure, and syncs records to an external system. It exposes Prometheus metrics and an observability web UI, and logs structured JSON to disk.

## Runtime and entry point

- Entry point: `src/ipat_watchdog/__main__.py` defines `main()` and is also registered as a console script `ipat-watchdog`.
- Env loading: on startup it loads a bundled `.env` from `build/.env` (when present). This mirrors the frozen app layout. You can still set environment variables in the OS; bundled values don’t override existing ones.
- Required env: `PC_NAME` must be set or the app exits; in the current code a fallback default of `tischrem_blb` is applied if missing.
- Device list: optional `DEVICE_PLUGINS` (comma/semicolon allowed) overrides device auto-selection. If not set, devices are inferred from the loaded PC plugin via `loader.get_devices_for_pc()`.
- Services started:
  - Prometheus metrics server on port 8000 (`prometheus_client.start_http_server`).
  - Observability server on port 8001 (Flask app served by Waitress).
- App wiring: constructs `ConfigService` from the PC plugin config and all device configs, calls `init_dirs()` to ensure folders exist, builds a `TKinterUI`, `UiInteractionAdapter`, and a `KadiSyncManager`, then runs `DeviceWatchdogApp`.

## Plugins (what exists right now)

Discovery is via Python entry points (see `pyproject.toml`) and loaded using `importlib.metadata.entry_points` in `loader.py`.

- Device plugins registered:
  - `sem_phenomxl2` → `SEMPhenomXL2Plugin`
  - `utm_zwick` → `UTMZwickPlugin`
  - `psa_horiba` → `PSAHoribaPlugin`
  - `dsv_horiba` → `DSVHoribaPlugin`
  - `test_device` → `TestDevicePlugin`
- PC plugins registered:
  - `tischrem_blb` → `PCTischREMPlugin`
  - `zwick_blb` → `PCZwickPlugin`
  - `horiba_blb` → `PCHoribaPlugin`
  - `test_pc` → `TestPCPlugin`

Each device plugin implements:

- `DevicePlugin.get_config() -> DeviceConfig`
- `DevicePlugin.get_file_processor() -> FileProcessorABS`

Each PC plugin implements:

- `PCPlugin.get_config() -> PCConfig`

The loader will raise `RuntimeError` with a helpful message if a named plugin isn’t installed.

## Configuration model

`core/config` provides a small runtime container and context helpers:

- `ConfigService(pc: PCConfig, devices: Iterable[DeviceConfig])` registers a PC config and one or more device configs.
- Device activation is scoped via `ConfigService.activate_device(device)` context manager and exposed through `current()`; helpers in `filesystem_utils` read from this active context.
- `ActiveConfig` exposes effective `paths`, `naming`, `watcher` and device metadata. Devices can override some PC-level behavior (e.g., session timeout, watcher settings).

You don’t need to know the PC or device file formats here; device and PC configs come from their respective plugin `settings.py` implementations.

## Logging and observability

- Logging: `core/logging/logger.py` sets up a JSON formatter and writes to `C:/Watchdog/logs/watchdog.log` with rotation. Logs also go to stdout when available.
- Observability: `observability.py` serves:
  - `GET /health` → `{"status": "ok"}`
  - `GET /logs?tail=N` → a simple HTML log viewer that pretty-prints JSON rows and supports client-side filtering.
  - The log path is configurable via `LOG_FILE_PATH` (defaults to `C:/Watchdog/logs/watchdog.log`).
  - Served by Waitress on `0.0.0.0:8001` in a daemon thread.

## Metrics (Prometheus)

Defined in `metrics.py` and exposed on `:8000`:

- `files_processed` (Counter)
- `files_processed_by_record{record_id=...}` (Counter)
- `files_failed` (Counter)
- `events_processed` (Counter)
- `file_process_time_seconds` (Histogram)
- `session_exit_status` (Gauge; 0=clean, 1=crashed)
- `session_duration_seconds` (Gauge)
- `exceptions_thrown` (Counter)

`DeviceWatchdogApp` updates these during lifecycle and on errors.

## File watching and UI

- `DeviceWatchdogApp` sets up a `watchdog` observer on the configured watch directory and places created files/folders onto a queue.
- The Tkinter UI (`core/ui/ui_tkinter.py`) is used for dialogs, warnings, and short prompts. The UI runs the event loop; file processing is scheduled periodically via `UiTaskScheduler`.

## Processing pipeline (as implemented)

Orchestrator: `core/processing/file_process_manager.py` with these steps:

1. Ignore internal staging artefacts: any path that matches `.__staged__` patterns is deferred.
2. Resolve device: `DeviceResolver` gathers all matching device configs (selector rules), probes candidates via `FileProcessorABS.probe_file()`, and chooses the best match. If none matches, the item is rejected and moved to exceptions.
3. Stability guard: `FileStabilityTracker.wait()` blocks until the file/folder is stable. It supports per-device overrides, temp file filters, and optional directory sentinels.
4. Preprocessing: `FileProcessorABS.device_specific_preprocessing(src)` may return `None` (defer until paired artefacts arrive) or a new effective path to continue with. A `.__staged__` suffix is stripped from names before parsing.
5. Parse and route: filename prefix and extension are parsed; `routing.fetch_record_for_prefix()` sanitizes and checks validity, looks up an existing record, then `routing.determine_routing_state()` decides among: ACCEPT, REQUIRE_RENAME, UNAPPENDABLE, APPEND_TO_SYNCED.
6. Rename flow: `RenameService` loops the user through a guided rename; on cancel, the item is moved to the rename folder and a friendly info message is shown.
7. Add to record: `add_item_to_record()` computes record and file IDs from config, calls the device `FileProcessorABS.device_specific_processing()` which returns `ProcessingOutput(final_path, datatype)`, updates the record model, and notifies the user.

### Processing pipeline (Mermaid)

```mermaid
sequenceDiagram
    title IPAT Watchdog – Processing Pipeline (ground truth)

    participant FS as Filesystem (watchdog)
    participant App as DeviceWatchdogApp
    participant FPM as FileProcessManager
    participant Res as DeviceResolver
    participant Cfg as ConfigService
    participant Fac as FileProcessorFactory
    participant Proc as FileProcessor (plugin)
    participant Stab as FileStabilityTracker
    participant Route as routing.py
    participant Ren as rename_flow.py
    participant RFlow as record_flow.py
    participant RUtil as record_utils.py
    participant FSU as filesystem_utils.py
    participant UI as UI (Tk/Adapter)
    participant Err as error_handling.py

    %% Event ingestion
    FS->>App: created(file|folder)
    App->>FPM: process_item(src_path)

    %% Early filter: internal staging ignore
    alt internal staging path (.__staged__)
      FPM-->>App: ProcessingResult(DEFERRED, "internal staging")
      return
    end

    %% Device resolution
    FPM->>Res: resolve(src_path)
    Res->>Cfg: matching_devices(src_path)
    alt no candidates
      FPM->>FSU: move_to_exception_folder(src_path)
      FPM-->>App: ProcessingResult(REJECTED, reason)
      return
    else one candidate
      Res-->>FPM: selected device (probe skipped)
    else multiple candidates
      loop probe candidates
        Res->>Fac: get_for_device(device_id)
        Fac-->>Res: Proc
        Res->>Proc: probe_file(src_path)
        Proc-->>Res: FileProbeResult
      end
      Res-->>FPM: selected device (best match/fallback)
    end

    %% Stability guard
    FPM->>Stab: wait()
    alt rejected (timeout/disappeared)
      FPM->>Err: safe_move_to_exception(src_path)
      FPM-->>App: ProcessingResult(REJECTED, reason)
      return
    else stable
      Stab-->>FPM: ok
    end

    %% Device-scoped processing
    FPM->>Cfg: activate_device(device)
    activate Cfg
    FPM->>Fac: get_for_device(device.identifier)
    Fac-->>FPM: Proc
    FPM->>Proc: device_specific_preprocessing(src_path)
    alt returns None (await pair)
      FPM-->>App: ProcessingResult(DEFERRED)
      deactivate Cfg
      return
    else returns effective_path
      FPM->>FSU: parse_filename(strip_stage_suffix(effective_path))
      FSU-->>FPM: (prefix, extension)
    end

    %% Routing
    FPM->>Route: fetch_record_for_prefix(records, prefix, device)
    Route-->>FPM: (sanitized_prefix, is_valid, record?)
    FPM->>Route: determine_routing_state(record, is_valid, prefix, extension, Proc)
    Route-->>FPM: decision

    alt UNAPPENDABLE
      FPM->>RFlow: handle_unappendable_record(UI, renameDelegate, context)
      RFlow->>Ren: obtain_valid_prefix(...)
      alt user cancels
        Ren->>FSU: move_to_rename_folder(...)
        UI<-FPM: info moved to rename
        FPM-->>App: ProcessingResult(REJECTED)
      else user provides valid prefix
        FPM: re-route with new prefix
      end

    else APPEND_TO_SYNCED
      FPM->>RFlow: handle_append_to_synced_record(UI, add_item_to_record, renameDelegate, context)

    else REQUIRE_RENAME
      FPM->>Ren: obtain_valid_prefix(current_prefix)
      alt user cancels
        Ren->>FSU: move_to_rename_folder(...)
        UI<-FPM: info moved to rename
        FPM-->>App: ProcessingResult(REJECTED)
      else user provides valid prefix
        FPM: re-route with new prefix
      end

    else ACCEPT
      FPM->>RUtil: get_or_create_record / apply_device_defaults
      FPM->>Proc: device_specific_processing(effective, record_path, file_id, extension)
      Proc-->>FPM: ProcessingOutput(final_path, datatype)
      FPM->>RUtil: update_record / manage_session
      UI<-FPM: notify_success(src_path, final_path)
      FPM-->>App: ProcessingResult(PROCESSED, final_path)
    end

    FPM->>Cfg: exit device context
    deactivate Cfg

    %% App surfaces rejections to UI
    App->>FPM: get_and_clear_rejected()
    FPM-->>App: [(path, reason), ...]
    loop per rejected item
      App->>UI: show_error("Unsupported Input", reason)
    end
```
8. On failures: items are moved to the exceptions folder; a rejection is queued for UI display; metrics are updated.

Key abstractions you will work with:

- `FileProcessorABS`: override `probe_file`, `matches_file`, `is_appendable`, `device_specific_preprocessing`, and must implement `device_specific_processing()`.
- `LocalRecord`: minimal record state with upload flags; JSON persisted via `filesystem_utils`.
- `RecordManager` and `SessionManager`: manage record lifecycle and session boundaries; app calls `sync_records_to_database()` on session end.

## Running locally (Windows PowerShell)

Install in editable mode with dev tools, then run the app. Ensure `PC_NAME` is set and that a `.env` exists at `build/.env` if you rely on it.

```powershell
# From repo root
python -m pip install -e .[dev]

# Minimal env (override DEVICE_PLUGINS to force devices if needed)
$env:PC_NAME = "tischrem_blb"
# optional: $env:DEVICE_PLUGINS = "sem_phenomxl2"

# Run
python -m ipat_watchdog
# or the console script
ipat-watchdog
```

Prometheus: http://localhost:8000/metrics

Observability UI: http://localhost:8001/logs and http://localhost:8001/health

## Tests (pytest)

- Install CI/test extras: the `ci` extra includes `pytest` and `pyfakefs`.
- Test helpers live under `tests/helpers` (fake UI, sync, processors, sessions).
- There are unit and integration tests; integration tests exercise filesystem flows.

```powershell
python -m pip install -e .[ci]
pytest
```

## Extending the system

Add a device plugin:

1. Create `src/ipat_watchdog/device_plugins/my_device/` with `plugin.py`, `settings.py`, and your `file_processor.py` implementing `FileProcessorABS`.
2. Register it in `pyproject.toml` under `[project.entry-points."ipat_watchdog.device_plugins"]`.
3. Provide an optional extra under `[project.optional-dependencies]` so users can `pip install ipat-watchdog[my_device]`.

Add a PC plugin:

1. Create `src/ipat_watchdog/pc_plugins/my_pc/` with `plugin.py` and `settings.py` that build a `PCConfig` and declare the active device plugin IDs.
2. Register it in `pyproject.toml` under `[project.entry-points."ipat_watchdog.pc_plugins"]`.
3. Set `PC_NAME=my_pc` (via OS env or `build/.env`).

## Guarantees and limitations (based on code)

- The app requires Windows paths in defaults (e.g., log directory is `C:/Watchdog`), but most logic is OS-agnostic.
- If `PC_NAME` or device entry points are missing, startup will fail with a clear error.
- Filename validation, sanitization, and routing are centralized in `core/storage/filesystem_utils.py` and `core/processing/routing.py`.
- Internal staging artefacts are ignored by design to avoid double-processing during preprocessing.

If you need deeper API details, browse the referenced modules alongside this guide; each section above maps directly to concrete files in `src/ipat_watchdog`.
    # Test implementation
```

**Test Helpers:**
- `FakeUI`: Mock UI for headless testing
- `FakeSyncManager`: Mock database sync for isolated tests
- `FakeFileProcessor`: Mock file processor for app-level tests

### Integration Testing

Integration tests use real filesystem monitoring:

```python
def test_end_to_end_processing(tmp_path):
    # Create test files
    test_file = tmp_path / "test-sample-001.dat"
    test_file.write_text("test data")
    
    # Run application
    app = create_test_app(watch_dir=tmp_path)
    # Verify processing
```

### Running Tests

```bash
# Install test dependencies
pip install ipat-watchdog[ci]

# Run all tests
pytest

# Run with coverage
pytest --cov=ipat_watchdog

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

## 📊 Monitoring and Debugging

### Prometheus Metrics

Access metrics at `http://localhost:8000/metrics`:

```
# HELP files_processed_total Total files processed by Watchdog
# TYPE files_processed_total counter
files_processed_total 42.0

# HELP session_duration_seconds Total duration of WatchdogApp session in seconds
# TYPE session_duration_seconds gauge
session_duration_seconds 1234.5
```

### Log Viewer

Access logs at `http://localhost:8001/logs`:

- Real-time log streaming
- JSON log parsing and formatting
- Client-side filtering
- Tail functionality (`?tail=100`)

### Health Checks

Monitor application health at `http://localhost:8001/health`:

```json
{"status": "ok"}
```

## 🚀 Deployment

### Development Environment

```bash
# Clone repository
git clone <repository-url>
cd ipat_data_watchdog

# Install in development mode
pip install -e .[dev]

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Set PC type for development (optional - defaults to tischrem_blb)
# PC_NAME=tischrem_blb

# Run application
python -m ipat_watchdog
```

### Production Deployment

```bash
# Install specific PC plugin configuration
pip install ipat-watchdog[tischrem_blb]

# Set environment for target PC
export PC_NAME=tischrem_blb

# Create Windows service (using PyInstaller)
pyinstaller --onefile --name wd-tischrem_blb src/ipat_watchdog/__main__.py
```

## 🔍 Common Development Patterns

### Adding New Configuration Options

1. Add to `BaseSettings` or device-specific settings class
2. Document in settings docstring
3. Add environment variable support if needed
4. Update tests to verify new setting

### Extending File Processing

1. Override methods in device-specific `FileProcessor`
2. Add device-specific validation rules
3. Implement metadata extraction for new file types
4. Update tests for new processing logic

### Adding New Sync Targets

1. Implement `ISyncManager` interface
2. Add configuration for new sync target
3. Implement error handling and retry logic
4. Add metrics for sync operations

### Custom UI Components

1. Extend `UserInterface` abstract class
2. Implement required methods for your UI framework
3. Add error handling and user feedback
4. Integrate with application lifecycle

## 📝 Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints throughout
- Write comprehensive docstrings
- Maintain test coverage above 80%

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation as needed
4. Ensure all tests pass
5. Submit PR with clear description

### Development Tools

```bash
# Code formatting
black src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/ tests/

# Testing
pytest --cov=ipat_watchdog
```

## 🐛 Troubleshooting

### Common Issues

**Plugin Not Found:**
- Verify plugin is installed: `pip list | grep ipat-watchdog`
- Check `PC_NAME` environment variable
- Verify entry point registration in `pyproject.toml`
- Ensure PC plugin exists and has valid device mappings

**File Processing Errors:**
- Check file permissions and ownership
- Verify directory structure matches settings
- Review logs for detailed error messages
- Test with minimal example files

**Database Sync Failures:**
- Verify network connectivity
- Check authentication credentials
- Review Kadi API status
- Check rate limiting and quotas

**UI Not Responding:**
- Check if running in service mode
- Verify display environment for GUI
- Review error logs for UI exceptions
- Test with headless mode

### Debug Mode

Enable verbose logging:

```bash
# Set in .env
LOG_LEVEL=DEBUG
PC_NAME=tischrem_blb

# Or environment variable
export LOG_LEVEL=DEBUG
export PC_NAME=tischrem_blb
python -m ipat_watchdog
```

## 📚 Additional Resources

- [Watchdog Library Documentation](https://python-watchdog.readthedocs.io/)
- [Kadi API Documentation](https://kadi.readthedocs.io/)
- [Prometheus Client Documentation](https://prometheus.github.io/client_python/)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)

---

For user-focused documentation, see `USER_README.md`.
For deployment guides, see the `docs/` directory.
