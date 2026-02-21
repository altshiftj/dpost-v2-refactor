# Deep-Core Runtime Retirement Inventory

## Title
- Inventory and execution baseline for retiring legacy deep-core runtime
  modules from canonical `dpost` runtime paths.

## Date
- 2026-02-21

## Context
- Phase 9-13 runtime boundary work is complete enough to begin the deep-core
  migration wave.
- Canonical runtime modules are now cleaner and route many legacy dependencies
  through explicit dpost boundary modules.
- Before implementing deeper rehost work, we need a precise inventory and
  ordered extraction map for processing, records, sync, and config internals.

## Findings
- Processing orchestration ownership is now rehosted in dpost:
  - `src/dpost/application/processing/file_process_manager.py`
  - `src/dpost/application/processing/` helper module set
- Storage utility ownership is now rehosted in dpost:
  - `src/dpost/infrastructure/storage/filesystem_utils.py`
- Record lifecycle and Kadi manager ownership seams are now dpost modules:
  - `src/dpost/application/records/record_manager.py`
  - `src/dpost/infrastructure/sync/kadi_manager.py`
- Remaining direct legacy imports under canonical dpost runtime/app paths are
  now concentrated in boundary modules for config/metrics and intentional UI/
  plugin namespace transition seams.
- Existing migration coverage is already strong and can support strict
  tests-first extraction.

## Evidence
- Remaining `ipat_watchdog` imports under `src/dpost`:
  - `src/dpost/application/config/__init__.py`
  - `src/dpost/application/metrics.py`
  - `src/dpost/infrastructure/runtime/desktop_ui.py`
  - `src/dpost/plugins/system.py`
- Legacy module complexity indicators:
  - `src/ipat_watchdog/core/config/runtime.py`
  - `src/ipat_watchdog/metrics.py`
- Existing migration gates currently green:
  - `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`

## Dependency Retirement Map
| Capability Surface | Current Legacy Owner | Current dpost Boundary | Target dpost Owner | Priority |
|---|---|---|---|---|
| Processing pipeline orchestration | rehosted under dpost | `dpost/application/processing/file_process_manager.py` | maintain and decompose within `dpost/application/processing/*` | done |
| Processing helper services/models | rehosted under dpost | `dpost/application/processing/*` | maintain and decompose within dpost ownership | done |
| Record lifecycle orchestration | rehosted under dpost | `dpost/application/records/record_manager.py` | maintain and decompose within `dpost/application/records/*` | done |
| Sync orchestration + Kadi implementation | rehosted manager seam under dpost | `dpost/infrastructure/sync/kadi.py`, `dpost/infrastructure/sync/kadi_manager.py` | maintain and decompose within dpost sync ownership | done |
| Config runtime lifecycle service | `core/config/runtime.py` | `infrastructure/runtime/config_dependencies.py` | `dpost/infrastructure/runtime/config_runtime.py` | P2 |
| Metrics registry ownership | `metrics.py` | `dpost/application/metrics.py` | native `dpost` metrics module with shared registry compatibility | P2 |
| Desktop UI concrete class | `core/ui/ui_tkinter.py` | `infrastructure/runtime/desktop_ui.py` | keep as legacy implementation until dedicated UI migration phase | P3 |

## Risks
- Processing refactor can introduce silent behavioral drift in route/retry/
  reject timing across device plugins.
- Record/sync extraction can alter immediate-sync side effects and operator
  visible failure messaging.
- Kadi adapter migration can break optional dependency behavior if lazy-import
  boundaries are not preserved.
- Late-stage import cleanup can remove required transition seams prematurely.

## Open Questions
- Should deep-core migration proceed by area or by layer?
  - Answer: by area, with tests-first capability slices (processing -> records
    -> sync -> config) to preserve behavior and reviewability.
- Should we delete boundary shim modules immediately after each area migrates?
  - Answer: yes, but only after area-specific migration contracts and global
    gates are green in the same change set.
- Should desktop UI class migration be included in deep-core runtime wave?
  - Answer: no. Keep desktop UI implementation stable for now; only maintain
    the import boundary during deep-core runtime retirement.
