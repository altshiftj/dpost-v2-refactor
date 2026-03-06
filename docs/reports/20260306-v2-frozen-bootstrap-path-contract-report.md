# Report: V2 Frozen Bootstrap and Path Contract

## Scope
- Goal:
  - make source and frozen startup resolve config and runtime paths
    deterministically
  - stop relative `paths.*` from depending on an arbitrary process working
    directory when a config file is supplied
  - keep the canonical `dpost` entrypoint path unchanged while preparing for
    PyInstaller

## Changes
- Added a deterministic bootstrap root hint in `src/dpost_v2/__main__.py`:
  - source mode uses the current working directory
  - frozen mode uses the executable directory
- Passed that root hint into bootstrap settings loading.
- Updated the settings service so that when `config_path` is supplied:
  - the config file is still located relative to the bootstrap root hint when
    needed
  - relative `paths.root`, `paths.watch`, `paths.dest`, and `paths.staging`
    resolve against the config file directory
- Left the canonical entrypoint unchanged:
  - `src/dpost/__main__.py` still delegates to the V2 main entrypoint

## Tests Added First
- `tests/dpost_v2/application/startup/test_settings_service.py`
  - relative runtime paths anchor to the config directory
- `tests/dpost_v2/test___main__.py`
  - V2 CLI passes the resolved bootstrap root hint into startup
  - source mode uses `cwd`
  - frozen mode uses the executable directory

## Validation
- `python -m pytest -q tests/dpost_v2/application/startup/test_settings_service.py -k "anchors_relative_runtime_paths_to_config_directory"`
  - passed
- `python -m pytest -q tests/dpost_v2/test___main__.py -k "bootstrap_root_hint or frozen_mode or source_mode"`
  - passed
- `python -m pytest -q tests/dpost_v2/application/startup tests/dpost_v2/test___main__.py`
  - passed

## Outcome
- Source and frozen startup now have an explicit root-hint model instead of
  relying on ambient process state.
- Config-driven relative runtime paths are now anchored to the config file
  directory, which is the cleaner workstation-executable behavior.
- The repo is ready to start the separate PyInstaller baseline slice on top of a
  clearer startup-path contract.

## Remaining Follow-On
- V2 PyInstaller build baseline
- hidden-import/plugin packaging proof
- manual source vs frozen workstation probe
