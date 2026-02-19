# Phase 6 Plugin and Discovery Hardening Inventory

## Date
- 2026-02-19

## Context
- Phase 5 is closed and green.
- Phase 6 starts with an inventory-first pass to lock plugin hygiene and
  discovery expectations before implementation changes.

## Inventory Scope
- Plugin package hygiene under:
  - `src/ipat_watchdog/device_plugins/`
  - `src/ipat_watchdog/pc_plugins/`
- Packaging alignment in:
  - `pyproject.toml` (`[project.optional-dependencies]`)
- Built-in plugin discovery behavior in:
  - `src/ipat_watchdog/plugin_system.py`

## Findings
| Area | Observation | Evidence |
|---|---|---|
| Package init naming hygiene | Four plugin packages use `_init_.py` and lack `__init__.py` (`erm_hioki`, `eirich_blb`, `hioki_blb`, `kinexus_blb`). | Source tree scan under `src/ipat_watchdog/device_plugins/` and `src/ipat_watchdog/pc_plugins/`. |
| Stale plugin directories | `psa_camsizer` exists as a device plugin directory but has no `plugin.py` or `settings.py`. | `src/ipat_watchdog/device_plugins/psa_camsizer/` contains only artifact content. |
| Optional dependency inventory alignment | Non-test plugin directories are not fully represented in optional groups because `psa_camsizer` has no matching group. | `pyproject.toml` optional groups vs non-test plugin directory names. |
| Built-in discovery coverage | `PluginLoader(load_builtins=True)` misses source plugins with misnamed init modules: `erm_hioki`, `eirich_blb`, `hioki_blb`, `kinexus_blb`. | Loader inventory compared to source packages with `plugin.py` and `settings.py`. |
| Discovery error actionability | Unknown plugin errors currently do not list available plugin names, limiting operator guidance. | `DevicePluginRegistry.create()` runtime error message in `src/ipat_watchdog/plugin_system.py`. |

## Phase 6 Tests-First Contract Added
- Added migration tests in:
  - `tests/migration/test_plugin_discovery_hardening.py`
- New failing expectations cover:
  - normalized plugin package init module naming
  - required plugin source modules (`plugin.py` + `settings.py`)
  - optional dependency group alignment with non-test plugin directories
  - built-in discovery parity with source plugin inventory
  - actionable unknown-plugin error messaging with available-plugin hints

## Update Addendum (2026-02-19)
- Implemented first hardening increment and moved tests to green by:
  - renaming `_init_.py` to `__init__.py` in `erm_hioki`, `eirich_blb`,
    `hioki_blb`, and `kinexus_blb`
  - removing stale `src/ipat_watchdog/device_plugins/psa_camsizer/`
  - updating unknown-plugin errors in `src/ipat_watchdog/plugin_system.py`
    to include available plugin names
- Verification after implementation:
  - `python -m pytest tests/migration/test_plugin_discovery_hardening.py`
    -> `5 passed`
  - `python -m pytest -m migration`
    -> `62 passed, 292 deselected`
