# IPAT Data Watchdog - Developer Documentation

## 🏗️ Architecture Overview

IPAT Data Watchdog is a modular, plugin-based scientific data ingestion system designed to monitor directories for incoming files from laboratory devices, process them according to device-specific rules, and synchronize the data to external databases. The application follows a clean architecture pattern with clear separation of concerns.

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
│   │   └── device_watchdog_app.py # Main application orchestrator
│   ├── config/
│   │   ├── settings_base.py       # Base configuration class
│   │   └── settings_store.py      # Global settings management
│   ├── handlers/
│   │   └── file_event_handler.py  # Filesystem event handling
│   ├── logging/
│   │   └── logger.py              # Structured logging setup
│   ├── processing/
│   │   ├── file_processor_abstract.py # File processing interface
│   │   └── file_process_manager.py    # File processing orchestration
│   ├── records/
│   │   ├── local_record.py        # Data record model
│   │   └── record_manager.py      # Record lifecycle management
│   ├── session/
│   │   └── session_manager.py     # Session handling and timeouts
│   ├── storage/
│   │   └── filesystem_utils.py    # File system utilities
│   ├── sync/
│   │   ├── sync_abstract.py       # Sync interface
│   │   └── sync_kadi.py           # Kadi database synchronization
│   └── ui/
│       ├── ui_abstract.py         # UI interface
│       ├── ui_tkinter.py          # Tkinter UI implementation
│       ├── ui_messages.py         # Standard UI messages
│       └── dialogs.py             # Custom dialog implementations
└── device_plugins/                # Device-specific implementations
    ├── device_plugin.py           # Plugin interface
    ├── sem_phenomxl2/          # SEM TischREM device plugin
    ├── psa_horibalinks_blb/       # PSA HoribaLinks device plugin
    └── utm_zwick/             # UTM Zwick device plugin
```

## 🔧 Key Components

### Application Entry Point (`__main__.py`)

The main entry point orchestrates the application startup:

1. **Environment Setup**: Loads `.env` configuration
2. **Plugin Loading**: Discovers and loads the appropriate device plugin
3. **Service Initialization**: 
   - Prometheus metrics server (port 8000)
   - Observability server with health checks and log viewer (port 8001)
4. **Application Assembly**: Wires together UI, sync manager, and file processor
5. **Application Startup**: Initializes and runs the main application

### Device Plugin System (`loader.py` + `device_plugins/`)

The plugin system uses Python entry points for automatic discovery:

```python
# In pyproject.toml
[project.entry-points."ipat_watchdog.device_plugins"]
sem_phenomxl2 = "ipat_watchdog.device_plugins.sem_phenomxl2.plugin:SEMPhenomXL2Plugin"
```

Each plugin must implement the `DevicePlugin` interface:

```python
class DevicePlugin(ABC):
    @abstractmethod
    def get_settings(self) -> BaseSettings:
        """Return device-specific configuration"""
        pass

    @abstractmethod
    def get_file_processor(self) -> FileProcessorBase:
        """Return device-specific file processor"""
        pass
```

### Main Application (`DeviceWatchdogApp`)

The central orchestrator coordinates all components:

- **Filesystem Monitoring**: Uses `watchdog` library to monitor directories
- **Event Processing**: Queues and processes file system events
- **UI Management**: Handles user interactions and error dialogs
- **Session Control**: Manages processing sessions with configurable timeouts
- **Metrics Collection**: Tracks performance and error metrics

**Key Methods:**
- `initialize()`: Sets up filesystem observer and UI
- `process_events()`: Main event loop for file processing
- `handle_exception()`: Global exception handling
- `end_session()`: Triggers database synchronization

### Configuration System (`core/config/`)

Configuration follows a hierarchical pattern:

1. **Base Settings** (`settings_base.py`): Common configuration options
2. **Device Settings**: Device-specific overrides in plugin directories
3. **Environment Variables**: Runtime configuration via `.env` files

**Key Configuration Areas:**
- Directory paths (watch, destination, exceptions)
- File naming patterns and validation rules
- Session timeouts and processing parameters
- Database connection settings
- Device metadata (user IDs, record types, tags)

### File Processing Pipeline (`core/processing/`)

The processing pipeline handles the complete file lifecycle:

1. **Event Detection**: Filesystem events trigger processing
2. **File Validation**: Check naming conventions and file integrity
3. **Metadata Extraction**: Extract device-specific metadata
4. **Record Creation**: Create or update data records
5. **File Organization**: Move files to appropriate directories
6. **Database Sync**: Upload metadata and files to external systems

**Abstract Interface:**
```python
class FileProcessorBase(ABC):
    @abstractmethod
    def validate_filename(self, filename: str) -> bool:
        """Validate file naming convention"""
        pass

    @abstractmethod
    def extract_metadata(self, file_path: Path) -> dict:
        """Extract device-specific metadata"""
        pass

    @abstractmethod
    def process_file(self, file_path: Path) -> LocalRecord:
        """Complete file processing workflow"""
        pass
```

### Record Management (`core/records/`)

Data records represent collections of related files from a single measurement:

- **LocalRecord**: Immutable data structure representing a measurement record
- **RecordManager**: Manages the lifecycle of records during a session
- **Persistence**: JSON serialization for record state and audit trails

### Session Management (`core/session/`)

Sessions group related files and determine when to sync to the database:

- **Automatic Sessions**: Start when files arrive, end after timeout
- **Manual Control**: UI controls for starting/ending sessions
- **Database Sync**: Triggered at session end
- **State Persistence**: Maintains session state across restarts

### Synchronization (`core/sync/`)

Database synchronization handles external data persistence:

- **Kadi Integration**: Primary implementation using `kadi-apy`
- **Batch Processing**: Efficient bulk uploads
- **Error Handling**: Retry logic and error reporting
- **Audit Trail**: Comprehensive logging of sync operations

### User Interface (`core/ui/`)

Minimal UI for error handling and user input:

- **Abstract Interface**: Pluggable UI implementations
- **Tkinter Implementation**: Cross-platform desktop UI
- **Dialog System**: Standardized error and input dialogs
- **Background Operation**: Non-blocking UI for service mode

### Observability (`metrics.py` + `observability.py`)

Comprehensive monitoring and debugging capabilities:

**Prometheus Metrics:**
- `files_processed`: Total files processed
- `files_failed`: Failed file processing attempts
- `session_duration`: Session length tracking
- `file_process_time`: Processing performance metrics

**Health Monitoring:**
- REST endpoints for health checks (`/health`)
- Web-based log viewer (`/logs`) with filtering
- Real-time metrics endpoint
- Structured JSON logging

## 🔌 Creating a New Device Plugin

### 1. Create Plugin Directory Structure

```
src/ipat_watchdog/device_plugins/my_device/
├── __init__.py
├── plugin.py              # Main plugin class
├── settings.py            # Device-specific settings
└── file_processor.py      # File processing logic
```

### 2. Implement Settings Class

```python
# settings.py
from ipat_watchdog.core.config.settings_base import BaseSettings
from typing import Set
import re

class MyDeviceSettings(BaseSettings):
    # Override base settings
    DEVICE_TYPE = "MY_DEVICE"
    ALLOWED_EXTENSIONS = {".dat", ".csv", ".log"}
    
    # Device-specific settings
    DEVICE_USER_KADI_ID = "my_device_user"
    RECORD_TAGS = ["My Device", "Automated"]
    
    # Custom filename pattern
    FILENAME_PATTERN = re.compile(r"^md-\w+-\d{8}\.dat$")
```

### 3. Implement File Processor

```python
# file_processor.py
from pathlib import Path
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorBase
from ipat_watchdog.core.records.local_record import LocalRecord

class MyDeviceFileProcessor(FileProcessorBase):
    def validate_filename(self, filename: str) -> bool:
        # Implement device-specific validation
        return filename.endswith('.dat')
    
    def extract_metadata(self, file_path: Path) -> dict:
        # Extract device-specific metadata
        return {
            "file_size": file_path.stat().st_size,
            "device_type": "My Device"
        }
    
    def process_file(self, file_path: Path) -> LocalRecord:
        # Implement complete processing workflow
        metadata = self.extract_metadata(file_path)
        # Create and return LocalRecord
        pass
```

### 4. Implement Plugin Class

```python
# plugin.py
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from .settings import MyDeviceSettings
from .file_processor import MyDeviceFileProcessor

class MyDevicePlugin(DevicePlugin):
    def __init__(self):
        self._settings = MyDeviceSettings()
        self._processor = MyDeviceFileProcessor()
    
    def get_settings(self):
        return self._settings
    
    def get_file_processor(self):
        return self._processor
```

### 5. Register Plugin in pyproject.toml

```toml
[project.entry-points."ipat_watchdog.device_plugins"]
my_device = "ipat_watchdog.device_plugins.my_device.plugin:MyDevicePlugin"

[project.optional-dependencies]
my_device = []  # Add any device-specific dependencies
```

### 6. Set Environment Variable

```bash
# In .env file
DEVICE_NAME=my_device
```

## 🧪 Testing

### Unit Testing

The project uses pytest with several testing utilities:

```python
# Example test structure
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from tests.helpers.fake_ui import FakeUI
from tests.helpers.fake_sync import FakeSyncManager

def test_file_processing():
    app = DeviceWatchdogApp(
        ui=FakeUI(),
        sync_manager=FakeSyncManager(),
        file_processor=TestFileProcessor()
    )
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

# Run application
python -m ipat_watchdog
```

### Production Deployment

```bash
# Install specific device plugin
pip install ipat-watchdog[sem_phenomxl2]

# Create Windows service (using PyInstaller)
pyinstaller --onefile --name wd-sem_phenomxl2 src/ipat_watchdog/__main__.py

# Install as Windows service
nssm install IPATWatchdog "C:\path\to\wd-sem_phenomxl2.exe"
nssm set IPATWatchdog Start SERVICE_AUTO_START
nssm start IPATWatchdog
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install .[sem_phenomxl2]

EXPOSE 8000 8001
CMD ["python", "-m", "ipat_watchdog"]
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
- Check `DEVICE_NAME` environment variable
- Verify entry point registration in `pyproject.toml`

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

# Or environment variable
export LOG_LEVEL=DEBUG
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
