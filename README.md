# dpost

`dpost` is a scientific data-ingestion watchdog for instrument workstations.
It watches local upload paths, routes artifacts to device processors, persists
record state, and can sync records through adapter boundaries.

## Project Status

- Canonical command name: `dpost`
- Canonical runtime package: `src/dpost_v2/`
- Canonical tests: `tests/dpost_v2/`
- Retired runtime architecture modes: `v1`, `shadow`
- Active UI/runtime modes: `headless` (default), `desktop`

## Architecture At A Glance

V2 code is organized by strict layer boundaries:

- `src/dpost_v2/domain/`: pure business/data rules.
- `src/dpost_v2/application/`: contracts, startup orchestration, ingestion flow,
  runtime/session coordination, record services.
- `src/dpost_v2/infrastructure/`: observability, storage, sync, runtime UI
  adapters.
- `src/dpost_v2/plugins/`: plugin contracts, discovery, host, profile
  selection, device/PC plugin namespaces.
- `src/dpost_v2/runtime/`: composition root and startup dependency resolution.

Reference docs:

- `docs/architecture/README.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/architecture-baseline.md`
- `docs/architecture/extension-contracts.md`

## Runtime Configuration

Primary environment variables:

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `DPOST_RUNTIME_MODE` | `headless`, `desktop` | `headless` | Select UI/runtime mode |
| `DPOST_SYNC_ADAPTER` | `noop`, `kadi` | `noop` | Select sync backend adapter |
| `DPOST_PLUGIN_PROFILE` | profile id | unset | Select plugin profile |
| `DPOST_PC_NAME` | plugin id | unset | Select PC plugin |
| `DPOST_DEVICE_PLUGINS` | csv/semicolon list | unset | Override active device plugins |

The transition-only architecture mode selector (`DPOST_MODE` values `v1`/`shadow`)
is retired for normal operation and should not be used.

## Installation

```powershell
python -m pip install .
```

Development install:

```powershell
python -m pip install -e ".[dev]"
```

Install repository git hooks:

```powershell
python -m pre_commit install
```

Optional Kadi backend:

```powershell
python -m pip install -e ".[kadi]"
```

## Quick Start

```powershell
$env:DPOST_PLUGIN_PROFILE = "reference"
$env:DPOST_RUNTIME_MODE = "headless"
$env:DPOST_SYNC_ADAPTER = "noop"
dpost
```

## Plugin Surface

- Device plugin namespace: `src/dpost_v2/plugins/devices/<plugin_name>/`
- PC plugin namespace: `src/dpost_v2/plugins/pcs/<plugin_name>/`
- Discovery root: `dpost_v2.plugins.devices` and `dpost_v2.plugins.pcs`
- Contract module: `dpost_v2.application.contracts.plugin_contracts`

Device plugin module exports must include:

- `metadata()`
- `capabilities()`
- `validate_settings(raw_settings)`
- `create_processor(settings)`

PC plugin module exports must include:

- `metadata()`
- `capabilities()`
- `create_sync_adapter(settings)`
- `prepare_sync_payload(record, context)`

## Development

Run active quality gates:

```powershell
python -m ruff check src/dpost_v2 tests/dpost_v2
python -m black --check src/dpost_v2 tests/dpost_v2
python -m pytest -q tests/dpost_v2
python -m pre_commit run --all-files
```

Optional parity checks for CI-equivalent subsets:

```powershell
python -m pytest -q tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/smoke
python -m pytest -q tests/dpost_v2/application/startup/test_bootstrap.py tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py
```

## Public CI

Workflow: `.github/workflows/public-ci.yml`

Required `main` check contexts:

- `workflow-lint`
- `quality (py3.12)`
- `quality (py3.13)`
- `unit-tests (py3.12)`
- `unit-tests (py3.13)`
- `integration-tests (py3.12)`
- `bootstrap-smoke`
- `artifact-hygiene`

## Documentation

- `USER_README.md`: operator/runtime usage guide
- `DEVELOPER_README.md`: contributor/developer guide
- `docs/architecture/README.md`: architecture documentation index

## License

MIT. See `LICENSE`.
