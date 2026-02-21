# Extension Contracts

## Purpose
- Define stable public extension contracts for `dpost` runtime contributors.
- Make supported plugin/sync extension surfaces explicit.
- Prevent accidental reintroduction of legacy namespace compatibility behavior.

## Canonical Runtime Extension Surface
- Runtime identity:
  - canonical startup is `python -m dpost` or `dpost`.
- Runtime mode selector:
  - `DPOST_RUNTIME_MODE` with values `headless` or `desktop`.
- Sync adapter selector:
  - `DPOST_SYNC_ADAPTER` with values `noop` or `kadi`.

## Plugin Discovery Contract
- Hook namespace:
  - `dpost` only.
- Hook decorators:
  - import from `dpost.plugins.system`:
    - `hookimpl`
    - `hookspec` (framework/internal use)
- Discovery groups:
  - device plugins: `dpost.device_plugins`
  - PC plugins: `dpost.pc_plugins`
- In-repo canonical package locations:
  - `src/dpost/device_plugins/<plugin_name>/`
  - `src/dpost/pc_plugins/<plugin_name>/`

## Device Plugin Contract
- Register using `register_device_plugins(registry)` with `@hookimpl`.
- Register a stable plugin identifier via `registry.register("<name>", Factory)`.
- Factory instance requirements:
  - `get_config() -> DeviceConfig-compatible object`
  - `get_file_processor() -> FileProcessorABS-compatible object`
- Device processor requirements:
  - implement `device_specific_processing(...)`
  - optional preprocessing/probe hooks per
    `dpost.application.processing.file_processor_abstract`.

## PC Plugin Contract
- Register using `register_pc_plugins(registry)` with `@hookimpl`.
- Register a stable plugin identifier via `registry.register("<name>", Factory)`.
- Factory instance requirements:
  - `get_config() -> PCConfig-compatible object`
- `PCConfig.active_device_plugins` must list device plugin identifiers.

## Sync Adapter Contract
- Application sync port:
  - `dpost.application.ports.sync.SyncAdapterPort`
- Required method:
  - `sync_record_to_database(local_record) -> bool`
- Optional interaction wiring:
  - adapters may expose `.interactions` for runtime interaction injection.

## Compatibility and Deprecation Policy
- Not supported in canonical dpost extension paths:
  - `ipat_watchdog` hook namespace markers.
  - legacy plugin namespace fallback in `src/dpost/**`.
  - legacy runtime startup identity as canonical contributor target.
- Compatibility wrappers under `src/ipat_watchdog/**` are retired and are not
  part of the canonical extension contract.

## Extension Test Expectations
- Minimum verification for extension changes:
  - targeted unit tests for plugin/sync behavior.
  - boundary tests where architecture ownership is affected.
  - full required gates:
    - `python -m ruff check .`
    - `python -m black --check .`
    - `python -m pytest`
