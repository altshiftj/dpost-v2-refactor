# dpost

This repository contains the `dpost` runtime and supporting architecture
artifacts.

## Current Entrypoints
- Canonical console script: `dpost` -> `dpost.__main__:main`
- Canonical module startup: `python -m dpost`

## Runtime Modes
- `DPOST_RUNTIME_MODE` controls startup mode in `dpost` composition:
  - `headless` (default): uses non-interactive `HeadlessRuntimeUI`.
  - `desktop`: uses `TKinterUI` to preserve desktop dialog/session behavior.
- `DPOST_SYNC_ADAPTER` selects sync adapter (`noop` default, `kadi` optional).
- `DPOST_PLUGIN_PROFILE=reference` is available for startup smoke paths.

## Key Docs
- `docs/architecture/README.md`
- `DEVELOPER_README.md`
- `USER_README.md`

## Test Split
- Archived compatibility characterization tests: `python -m pytest -m legacy`
- Full suite: `python -m pytest`
