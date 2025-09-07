# PC Plugin System

This document describes thEach PC plugin defines its compatible devices through the `get_active_device_plugins()` method in its settings class. The mapping automatically associates each PC type with its compatible devices:

- **tischrem_blb**: TischREM lab environment with SEM TischREM  
- **zwick_blb**: Zwick testing environment with UTM Zwick machine
- **horiba_blb**: Horiba lab environment with PSA and DSV Horiba devices

Simply set `PC_NAME` in your environment - the appropriate devices will be loaded automatically.gin architecture for customizing application behavior based on the target PC environment.

## Overview

The PC plugin system allows you to customize application settings and behavior for different PC environments at build time. This complements the existing device plugin system by providing PC-specific configuration.

## Architecture

```
src/ipat_watchdog/
├── pc_plugins/
│   ├── __init__.py
│   ├── pc_plugin.py              # Base PCPlugin interface
│   ├── tischrem_blb/             # TischREM lab configuration
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   └── settings.py
│   ├── zwick_blb/                # Zwick testing configuration
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   └── settings.py
│   └── horiba_blb/               # Horiba lab configuration
│       ├── __init__.py
│       ├── plugin.py
│       └── settings.py
```

## Usage

### Environment Configuration

Set the `PC_NAME` environment variable to specify which PC plugin to load. The associated device plugins are automatically determined by the PC plugin's settings:

```bash
# In .env file or CI environment
PC_NAME=tischrem_blb       # Loads: sem_phenomxl2
PC_NAME=zwick_blb          # Loads: utm_zwick
PC_NAME=horiba_blb         # Loads: psa_horiba, dsv_horiba
```

## PC-Device Mapping

Each PC plugin defines its compatible devices through the `get_active_device_plugins()` method in its settings class. The mapping automatically associates each PC type with its compatible devices:

- **tischrem_blb**: TischREM lab environment with SEM TischREM  
- **zwick_blb**: Zwick testing environment with UTM Zwick machine
- **horiba_blb**: Horiba lab environment with PSA and DSV Horiba devices

Simply set `PC_NAME` in your environment - the appropriate devices will be loaded automatically.

### Build Integration

PC plugins are loaded automatically during application startup:

```python
# In __main__.py
pc_name = os.getenv("PC_NAME")
if not pc_name:
    pc_name = "tischrem_blb"  # Development fallback
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
    
    def get_active_device_plugins(self) -> list[str]:
        """Return list of device plugins for this PC."""
        return ["my_device"]

# plugin.py
class MyPCPlugin(PCPlugin):
    def __init__(self):
        self._settings = MyPCSettings()
    
    def get_settings(self) -> PCSettings:
        return self._settings
```

## Available PC Plugins

- **tischrem_blb**: TischREM lab workstation configuration
- **zwick_blb**: Zwick testing machine configuration  
- **horiba_blb**: Horiba lab configuration with PSA and DSV devices
- **test_pc**: Test configuration for development

## Build System Integration

PC plugins integrate with the existing build system by specifying the PC_NAME in your build environment, similar to how DEVICE_NAME works for device plugins.

The SettingsManager will use PC plugin settings as the global settings, combining them with device-specific settings through the CompositeSettings system.
