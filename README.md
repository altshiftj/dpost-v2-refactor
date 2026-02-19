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
- `DPOST_PLUGIN_PROFILE=reference` is available for migration-safe startup
  smoke paths.

## Key Docs
- `docs/architecture/README.md`
- `docs/planning/20260218-dpost-architecture-tightening-plan.md`
- `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`
- `docs/planning/20260218-dpost-execution-board.md`
- `docs/reports/20260219-phase8-cutover-migration-notes.md`
- `docs/planning/20260219-post-sunset-compatibility-retirement-plan.md`
- `docs/checklists/20260219-post-sunset-compatibility-retirement-checklist.md`
- `docs/planning/20260219-post-sunset-compatibility-retirement-pr-runbook.md`

## Test Split
- Legacy behavior contract tests: `python -m pytest -m legacy`
- Migration/cutover tests: `python -m pytest -m migration`
- Full suite: `python -m pytest`
