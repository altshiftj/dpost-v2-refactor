# PC Plugin System

This document describes the PC plugin architecture for customizing application behavior based on the target PC environment.

## Overview

The PC plugin system allows you to customize application settings and behavior for different PC environments at build time. This complements the existing device plugin system by providing PC-specific configuration.

## Architecture

```
src/ipat_watchdog/
├── pc_plugins/
│   ├── __init__.py
│   ├── pc_plugin.py              # Base PCPlugin interface
│   ├── default_pc_blb/           # Default PC configuration
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   └── settings.py
│   └── lab_workstation_blb/      # Lab workstation configuration
│       ├── __init__.py
│       ├── plugin.py
│       └── settings.py
```

## Usage

### Environment Configuration

Set the `PC_NAME` environment variable in your `.env` file to specify which PC plugin to load:

```bash
# In .env file
PC_NAME=default_pc_blb    # Use default PC settings
PC_NAME=lab_workstation_blb    # Use lab workstation settings
```

The `.env` file contains all environment configuration in one place:
- `PC_NAME`: Which PC plugin to use
- `DEVICE_NAMES`: Which device plugins to load (comma-separated)
- `DEVICE_NAME`: Legacy single device name for build scripts

### Build Integration

PC plugins are loaded automatically during application startup:

```python
# In __main__.py
pc_name = os.getenv("PC_NAME", "default_pc_blb")
pc_plugin = load_pc_plugin(pc_name.strip())
pc_settings = pc_plugin.get_settings()
```

### Creating New PC Plugins

1. Create a new directory in `src/ipat_watchdog/pc_plugins/`
2. Implement the plugin class extending `PCPlugin`
3. Create settings class extending `PCSettings`
4. Register in `pyproject.toml`

Example:

```python
# settings.py
class MyPCSettings(PCSettings):
    WATCH_DIR = Path("C:\\MyCustomPath\\Upload")
    POLL_SECONDS = 1.0

# plugin.py
class MyPCPlugin(PCPlugin):
    def __init__(self):
        self._settings = MyPCSettings()
    
    def get_settings(self) -> PCSettings:
        return self._settings
```

## Available PC Plugins

- **default_pc_blb**: Standard configuration using base PCSettings
- **lab_workstation_blb**: Lab environment with faster polling and custom paths

## Build System Integration

PC plugins integrate with the existing build system by specifying the PC_NAME in your build environment, similar to how DEVICE_NAME works for device plugins.

The SettingsManager will use PC plugin settings as the global settings, overriding the default PCSettings.
