# ipat-watchdog (Migrating to dpost)

This repository contains the current `ipat_watchdog` implementation and an in-progress migration scaffold for `dpost`.

## Current Entrypoints
- Legacy: `ipat-watchdog` -> `ipat_watchdog.__main__:main`
- Migration scaffold: `dpost` -> `dpost.__main__:main`

## Migration Status
- Headless-first migration is active.
- Optional sync-adapter architecture is planned.
- Architecture governance docs live under `docs/architecture/`.

## Key Docs
- `docs/architecture/README.md`
- `docs/planning/20260218-dpost-architecture-tightening-plan.md`
- `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`
- `docs/planning/20260218-dpost-execution-board.md`

## Test Split
- Legacy behavior contract tests: `python -m pytest -m legacy`
- Migration/cutover tests: `python -m pytest -m migration`
- Full suite: `python -m pytest`

