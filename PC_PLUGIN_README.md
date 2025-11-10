# PC Plugin System

PC plugins provide workstation-level configuration for IPAT Data Watchdog. A PC plugin returns a `PCConfig` object that lists the device plugins to activate and can override filesystem, naming, session, or watcher defaults. `DeviceWatchdogApp` loads exactly one PC plugin at startup, based on the `PC_NAME` environment variable.

Unlike earlier iterations of the documentation, there is **no** `get_active_device_plugins()` helper on a settings class. The active device identifiers live directly in `PCConfig.active_device_plugins`, and the plugin simply returns this configuration through `PCPlugin.get_config()`.

## Project Layout
```
src/ipat_watchdog/
|-- pc_plugins/
|   |-- __init__.py
|   |-- pc_plugin.py            # Base PCPlugin ABC
|   |-- tischrem_blb/
|   |   |-- plugin.py           # Registers PCTischREMPlugin via @hookimpl
|   |   `-- settings.py         # build_config() -> PCConfig
|   |-- horiba_blb/
|   |-- zwick_blb/
|   |-- haake_blb/
|   |-- kinexus_blb/
|   `-- test_pc/
```

Each plugin directory contains a `settings.py` that exposes a `build_config()` helper and a `plugin.py` that registers a concrete `PCPlugin` implementation.

## Startup Behaviour
`core/app/bootstrap.collect_startup_settings()` reads `PC_NAME`, loads the corresponding plugin via `loader.load_pc_plugin(pc_name)`, and calls `get_config()`. When `DEVICE_PLUGINS` is not set, the device list is taken from `PCConfig.active_device_plugins`. Helper `loader.get_devices_for_pc(pc_name)` reuses the same logic when other tools need to know the active devices.

The resulting `PCConfig` is passed into `init_config()`, which seeds the global `ConfigService`. Any overrides you place on `PathSettings`, `NamingSettings`, or `WatcherSettings` are therefore visible throughout the processing pipeline.

## Bundled PC Plugins
| PC plugin     | Active device plugins                     | Notes                                  |
|---------------|-------------------------------------------|----------------------------------------|
| `tischrem_blb`| `sem_phenomxl2`                           | Tisch REM microscope workstation       |
| `horiba_blb`  | `psa_horiba`, `dsv_horiba`                | Horiba particle analysis setup         |
| `zwick_blb`   | `utm_zwick`                               | BLB tensile testing workstation        |
| `haake_blb`   | `extr_haake`                              | Haake twin-screw extruder              |
| `kinexus_blb` | `rhe_kinexus`                             | Kinexus rheometer workstation          |
| `test_pc`     | `test_device`                             | Used by automated tests; overrideable paths |

All bundled plugins currently rely on the default `PathSettings`, so they share the same `Desktop\Upload` / `Desktop\Data` layout. Custom plugins can override these settings if the workstation organises data differently.

## Working with `PCConfig`
`core/config/schema.py` defines the full shape of `PCConfig`:

- `identifier`: canonical plugin name (used in logging/metrics).
- `name`, `location`: optional metadata for display.
- `paths`: `PathSettings` (watch directory, destination folders, etc.).
- `naming`: `NamingSettings` (separators, filename regex).
- `session`: `SessionSettings` (timeouts and prompts).
- `watcher`: `WatcherSettings` (poll rates, stability thresholds).
- `active_device_plugins`: sequence of device plugin identifiers.

Most plugins simply set the identifier and `active_device_plugins`. You can override any of the other fields by instantiating and mutating the relevant dataclasses before returning the `PCConfig`.

### Example Override
```python
# src/ipat_watchdog/pc_plugins/my_pc/settings.py
from pathlib import Path
from ipat_watchdog.core.config import PCConfig, PathSettings


def build_config() -> PCConfig:
    paths = PathSettings()
    paths.watch_dir = Path(r"D:\Instruments\Upload")
    paths.dest_dir = Path(r"D:\Instruments\Data")

    return PCConfig(
        identifier="my_pc",
        name="My Lab Workstation",
        location="BLB Lab 3",
        paths=paths,
        active_device_plugins=("sem_phenomxl2", "psa_horiba"),
    )
```

```python
# src/ipat_watchdog/pc_plugins/my_pc/plugin.py
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.plugin_system import hookimpl
from .settings import build_config


class MyPCPlugin(PCPlugin):
    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self):
        return self._config


@hookimpl
def register_pc_plugins(registry):
    registry.register("my_pc", MyPCPlugin)
```

Register the new plugin under `[project.entry-points."ipat_watchdog.pc_plugins"]` in `pyproject.toml` so that Pluggy can discover it when the package is installed.

## Troubleshooting
- **"No PC plugin named '<value>'"** - confirm `PC_NAME` matches the identifier used in `registry.register()`.
- **Devices missing at runtime** - ensure `PCConfig.active_device_plugins` lists the correct identifiers, or set `DEVICE_PLUGINS` to override during testing.
- **Custom paths not respected** - verify your plugin returns a single cached `PCConfig` instance and that it modifies `PathSettings` before caching.
- **Multiple workstation variants** - create separate PC plugins, each returning a tailored `PCConfig`, and choose the correct one via `PC_NAME`.

For details on the wider architecture, consult `DEVELOPER_README.md`. For operator instructions, see `USER_README.md`.
