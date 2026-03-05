# Extension Contracts

## Purpose

- Define stable extension contracts for active V2 `dpost` runtime contributors.
- Keep plugin and adapter surfaces explicit and deterministic.

## Canonical Runtime Extension Surface

- Command identity: `dpost`
- Runtime package: `dpost_v2`
- Runtime mode selector: `DPOST_RUNTIME_MODE` (`headless`, `desktop`)
- Sync adapter selector: `DPOST_SYNC_ADAPTER` (`noop`, `kadi`)

Retired architecture modes (`v1`, `shadow`) are not part of the active
extension contract.

## Plugin Discovery Contract

- Device namespace root: `dpost_v2.plugins.devices`
- PC namespace root: `dpost_v2.plugins.pcs`
- In-repo package locations:
  - `src/dpost_v2/plugins/devices/<plugin_name>/`
  - `src/dpost_v2/plugins/pcs/<plugin_name>/`
- Discovery/host boundary:
  - `src/dpost_v2/plugins/discovery.py`
  - `src/dpost_v2/plugins/host.py`

## Shared Plugin Contract Types

Defined in `dpost_v2.application.contracts.plugin_contracts`:

- `PluginMetadata`
- `PluginCapabilities`
- `ProcessorContract`
- `ProcessorResult`
- `PLUGIN_CONTRACT_VERSION`

## Device Plugin Contract

Each device plugin module must export callable functions:

- `metadata()` -> `PluginMetadata` or mapping
- `capabilities()` -> `PluginCapabilities` or mapping
- `validate_settings(raw_settings)`
- `create_processor(settings)` -> `ProcessorContract`

Optional lifecycle hooks:

- `on_activate(context)`
- `on_shutdown()`

## PC Plugin Contract

Each PC plugin module must export callable functions:

- `metadata()` -> `PluginMetadata` or mapping
- `capabilities()` -> `PluginCapabilities` or mapping
- `create_sync_adapter(settings)`
- `prepare_sync_payload(record, context)`

Optional lifecycle hooks may include `before_sync`, `after_sync`, and
`on_shutdown`.

## Sync Adapter Contract

Application sync boundary is defined in
`dpost_v2.application.contracts.ports.SyncPort`.

Required method:

- `sync_record(request: SyncRequest) -> SyncResponse`

Concrete adapters live under `src/dpost_v2/infrastructure/sync/`.

## Compatibility and Deprecation Policy

- Not supported for active contributor targets:
  - legacy `src/dpost/**` runtime surfaces
  - legacy test lanes (`tests/unit`, `tests/integration`, `tests/manual`)
  - retired architecture modes (`v1`, `shadow`)
- Historical migration docs may retain legacy references only when marked as
  archive.

## Extension Test Expectations

Minimum verification for extension changes:

- targeted contract tests under `tests/dpost_v2/`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
- `python -m black --check src/dpost_v2 tests/dpost_v2`
- `python -m pytest -q tests/dpost_v2`
