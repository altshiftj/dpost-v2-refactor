# Phase 4 Runtime Config-Read Inventory

## Date
- 2026-02-18

## Context
- Phase 3 closed with migration tests green (`16 passed`).
- Phase 4 starts with a required inventory of runtime config reads (environment + legacy constants) before consolidation.

## Environment Read Inventory
| Config key | Read location | Current fallback/default | Operational use |
|---|---|---|---|
| `DPOST_SYNC_ADAPTER` | `src/dpost/runtime/composition.py:19` | `"noop"` | Selects sync adapter before bootstrap; selected adapter is injected via `sync_manager_factory` into legacy bootstrap wiring. |
| `DPOST_PLUGIN_PROFILE` | `src/dpost/runtime/composition.py:47` | empty string (disabled) | Enables profile mapping (`reference`) and injects explicit startup settings for kernel validation paths. |
| `PC_NAME` | `src/ipat_watchdog/core/app/bootstrap.py:130` | required (`MissingConfiguration` if empty) | Determines which PC plugin config is loaded during startup. |
| `DEVICE_PLUGINS` | `src/ipat_watchdog/core/app/bootstrap.py:134` | if empty, infer from PC plugin mapping | Determines active device plugin set at startup. |
| `PROMETHEUS_PORT` | `src/ipat_watchdog/core/app/bootstrap.py:142` | `8000` | Controls Prometheus HTTP metrics port in bootstrap. |
| `OBSERVABILITY_PORT` | `src/ipat_watchdog/core/app/bootstrap.py:144` | `8001` | Controls optional observability server port in bootstrap. |
| `LOG_FILE_PATH` | `src/ipat_watchdog/observability.py:9` | `C:/Watchdog/logs/watchdog.log` | Defines log file source for `/logs` observability endpoint. |
| `USERPROFILE` / `HOME` | `src/ipat_watchdog/core/config/schema.py:29` | `Path.home()` when both unset | Seeds default desktop/path settings in config schema. |
| `USERPROFILE` | `src/ipat_watchdog/core/config/constants.py:10` | none (direct index access) | Computes legacy desktop-derived constant paths at import time. |

## Legacy Constant Read Inventory (Operational Paths)
| Legacy constant source | Read location | Runtime effect |
|---|---|---|
| `DIRECTORY_LIST`, `DEST_DIR`, `RENAME_DIR`, `EXCEPTIONS_DIR`, `DAILY_RECORDS_JSON`, `ID_SEP`, `FILE_SEP`, `FILENAME_PATTERN` | `src/ipat_watchdog/core/storage/filesystem_utils.py:39`, `src/ipat_watchdog/core/storage/filesystem_utils.py:46`, `src/ipat_watchdog/core/storage/filesystem_utils.py:53`, `src/ipat_watchdog/core/storage/filesystem_utils.py:60`, `src/ipat_watchdog/core/storage/filesystem_utils.py:67`, `src/ipat_watchdog/core/storage/filesystem_utils.py:74`, `src/ipat_watchdog/core/storage/filesystem_utils.py:81`, `src/ipat_watchdog/core/storage/filesystem_utils.py:88` | Used when config service is unavailable (`current()` raises). These fallbacks affect directory initialization, routing destinations, filename validation, and persisted record path resolution in active processing code paths. |
| `ID_SEP` | `src/ipat_watchdog/core/records/local_record.py:7` and `src/ipat_watchdog/core/records/local_record.py:39` | Record identifier parsing/normalization is fixed to legacy separator constant rather than active config naming settings. |
| `ID_SEP` | `src/ipat_watchdog/core/sync/sync_kadi.py:10` and ID construction sites (for example `src/ipat_watchdog/core/sync/sync_kadi.py:62`) | Kadi user/group/collection identifier composition is fixed to legacy separator constant. |
| `ID_SEP` (fallback) | `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py:50`, `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py:46` | Plugin sequencing names use config-service separator when available, but still fall back to legacy constant when service is missing. |

## Operational Call-Site Evidence
- Bootstrap invokes directory initialization through filesystem utils: `src/ipat_watchdog/core/app/bootstrap.py:85`.
- Processing/routing path generation depends on filesystem utils (`get_record_path`, `generate_file_id`, exception/rename moves): `src/ipat_watchdog/core/processing/file_process_manager.py:338`, `src/ipat_watchdog/core/processing/file_process_manager.py:339`, `src/ipat_watchdog/core/processing/error_handling.py:21`.
- Persisted record load/save path uses filesystem utils in record manager: `src/ipat_watchdog/core/records/record_manager.py:55`, `src/ipat_watchdog/core/records/record_manager.py:145`.

## Findings
- Runtime startup config is currently split between dpost composition env reads and legacy bootstrap env reads.
- Operational filesystem/routing code still contains fallback dependency on legacy constants when config service is not initialised.
- Naming semantics (`ID_SEP`) remain partially hardwired to legacy constants in record + sync modules.
- Legacy constants derive desktop paths at import time using `os.environ["USERPROFILE"]`, which is brittle for non-Windows/headless environments.

## Phase 4 Consolidation Targets (Derived)
- Introduce a single composition-time config resolver for startup behavior and bootstrap settings.
- Remove operational fallback reliance on `core/config/constants.py` in runtime code paths where config service should be authoritative.
- Preserve behavior with migration tests for default, explicit override, and env-driven bootstrap config scenarios before implementation changes.

## Update Addendum (2026-02-18)
- `src/ipat_watchdog/core/storage/filesystem_utils.py` operational constants fallback has been removed.
- Separator reads were migrated off legacy constants in:
  `src/ipat_watchdog/core/records/local_record.py`,
  `src/ipat_watchdog/core/sync/sync_kadi.py`,
  `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`, and
  `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`.
- Migration verification after these increments:
  `python -m pytest -m migration`
  -> `25 passed, 292 deselected`.
- Remaining consolidation caveat:
  `local_record` and `sync_kadi` still keep a compatibility separator default
  when config service is unavailable; strict fail-fast fallback elimination is
  still pending.
