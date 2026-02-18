# Codebase Overview: ipat-watchdog (Pre-dpost Migration)

## Date
- 2026-02-18

## Scope
- `pyproject.toml`
- `src/ipat_watchdog/`
- `tests/`

## Project Snapshot
- Distribution name: `ipat-watchdog`
- Import root: `ipat_watchdog`
- CLI entrypoint: `ipat-watchdog = ipat_watchdog.__main__:main`
- Python requirement in packaging: `>=3.10`
- Runtime dependencies: `kadi-apy`, `watchdog`, `prometheus_client`, `python-dotenv`, `requests`, `pywin32`, `pywin32-ctypes`, `PyYAML`, `flask`, `waitress`, `pluggy`
- Source size: 120 Python files in `src/ipat_watchdog` (~7,395 LOC)
- Test size: 82 Python files in `tests` (~5,047 LOC)
- Test functions found: 243

## Runtime Architecture
1. Entrypoint and startup
- `src/ipat_watchdog/__main__.py` calls `bootstrap()` and then `context.app.run()`.
- `src/ipat_watchdog/core/app/bootstrap.py` resolves env-driven startup settings, loads PC/device plugins, initializes config service and directories, then starts Prometheus and optional observability HTTP server.

2. App loop and file watching
- `src/ipat_watchdog/core/app/device_watchdog_app.py` owns the observer lifecycle.
- Filesystem events are pushed to a queue by watchdog handler threads.
- Actual processing is executed on scheduled UI ticks, keeping processing logic single-threaded.

3. Processing pipeline
- `src/ipat_watchdog/core/processing/file_process_manager.py` is the orchestration center.
- Flow: device resolution -> stability wait -> device preprocessing -> routing/rename decisions -> record update -> optional immediate sync.
- Routing decisions are represented by typed models in `src/ipat_watchdog/core/processing/models.py`.

4. Persistence and sync
- `src/ipat_watchdog/core/records/record_manager.py` handles local record state and persistence.
- `src/ipat_watchdog/core/records/local_record.py` tracks file-level sync status.
- `src/ipat_watchdog/core/sync/sync_kadi.py` uploads records/files to Kadi using `kadi_apy`.

## Plugin and Configuration Model
- Plugin system: `src/ipat_watchdog/plugin_system.py` (pluggy-based, lazy loading, singleton loader).
- Plugin contracts:
- `src/ipat_watchdog/device_plugins/device_plugin.py`
- `src/ipat_watchdog/pc_plugins/pc_plugin.py`
- PC plugins provide workstation config including `active_device_plugins`.
- Device plugins provide `DeviceConfig` and processor instance.
- Config schema is dataclass-first in `src/ipat_watchdog/core/config/schema.py`.
- Active config context is handled by `ConfigService` + `ContextVar` in `src/ipat_watchdog/core/config/service.py`.

### Built-in plugin inventory (from source tree)
- Device plugin dirs: 11 (`dsv_horiba`, `erm_hioki`, `extr_haake`, `psa_camsizer`, `psa_horiba`, `rhe_kinexus`, `rmx_eirich_el1`, `rmx_eirich_r01`, `sem_phenomxl2`, `test_device`, `utm_zwick`)
- PC plugin dirs: 8 (`eirich_blb`, `haake_blb`, `hioki_blb`, `horiba_blb`, `kinexus_blb`, `test_pc`, `tischrem_blb`, `zwick_blb`)

## UI, Logging, and Observability
- UI abstraction is defined in `src/ipat_watchdog/core/ui/ui_abstract.py`; default implementation is Tkinter (`ui_tkinter.py`).
- Domain-facing UI ports live under `src/ipat_watchdog/core/interactions/` and are adapted in `src/ipat_watchdog/core/ui/adapters.py`.
- Logging uses JSON lines with rotating file handler in `src/ipat_watchdog/core/logging/logger.py`.
- Default log path is hardcoded to `C:/Watchdog/logs/watchdog.log`.
- Prometheus metrics are defined in `src/ipat_watchdog/metrics.py` and started on bootstrap.
- Optional Flask + Waitress observability service lives in `src/ipat_watchdog/observability.py`.

## Test Topology
- Test split:
- `tests/unit` (61 Python files)
- `tests/integration` (8 Python files)
- `tests/manual` (2 Python files)
- Shared fixtures and helpers:
- `tests/conftest.py`
- `tests/helpers/*` (headless UI, fake observer/sync/processor/session, scheduler drain utilities)
- Coverage focus appears strong in:
- processing pipeline behavior
- device-specific processors and pairing/deferral logic
- plugin loading behavior
- app bootstrap and runtime flow
- config schema/service behavior

## Strengths for Open-source Migration
- Clear domain split between core orchestration and device/PC plugin modules.
- Strongly typed config schema with explicit dataclasses.
- Plugin loading is already modular and supports lazy discovery.
- Processing pipeline is testable and has substantial unit/integration coverage.
- Interactions are abstracted behind ports, supporting UI replacement.

## Migration Risks and Standardization Targets
- Packaging metadata gap: `pyproject.toml` references `README.md`, but repository currently has no `README.md` at root.
- Mixed configuration sources: `core/config/schema.py` and `core/config/constants.py` overlap in defaults; `filesystem_utils.py` can still fall back to constants.
- Windows-specific hardcoded paths in runtime logging/config defaults (`C:/Watchdog`, desktop-derived paths), which limits portability.
- Startup is UI-first (`TKinterUI` default in bootstrap), making headless/server deployment less straightforward.
- Naming inconsistencies in package files (`_init_.py` in multiple plugin packages).
- One device plugin directory (`psa_camsizer`) currently contains only `__pycache__` artifacts (no source module).
- Legacy test expectation exists for non-present plugin names (`twinscrew_blb`, `etr_twinscrew`) in `tests/unit/loader/test_pc_device_mapping.py`.
- Minor hygiene signal: duplicated trailing module string literal in `src/ipat_watchdog/core/config/__init__.py`.

## Suggested First Standardization Wave (for dpost)
1. Identity and packaging
- Rename distribution/import namespaces and create a canonical root `README.md`.
- Decide public API surface and freeze import boundaries before broad refactors.

2. Configuration consolidation
- Remove fallback dependency on `core/config/constants.py` after schema-based runtime config is fully authoritative.
- Centralize path policy so defaults are environment-agnostic.

3. Runtime modes
- Separate headless runtime from interactive Tk runtime at bootstrap level.
- Keep interaction ports, but make UI implementation selectable by mode.

4. Plugin hygiene
- Normalize package init file names and clean dead/stale plugin directories.
- Align optional dependency groups in `pyproject.toml` with actual plugin inventory.

5. Test contract tightening
- Keep unit/integration structure, but update outdated mapping expectations.
- Add a small CI smoke matrix for plugin discovery + bootstrap paths (headless and UI).

## Update Addendum (2026-02-18)
- `src/dpost/` scaffold has been created with a dedicated runtime composition module:
- `src/dpost/runtime/composition.py`
- New script entrypoint added:
- `dpost = "dpost.__main__:main"` in `pyproject.toml`
- Test isolation has been introduced via pytest markers:
- `legacy` for existing `ipat_watchdog` contract tests
- `migration` for `dpost` migration/cutover tests under `tests/migration/`

## Open Questions
- Runtime posture has been decided as headless-first; monitor if this needs revision after desktop reintegration.
- Sync direction has been decided as optional adapter model; next question is adapter packaging boundaries.
- Do you want each device/PC plugin to remain in-repo, or evolve toward external plugin packages via entry points?
- For open-source release, should Windows path defaults be preserved as defaults, or moved to explicit `.env`/config inputs only?
