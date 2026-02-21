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
- `docs/planning/20260221-part3-domain-layer-extraction-roadmap.md`
- `docs/checklists/20260221-part3-domain-layer-extraction-checklist.md`
- `docs/reports/20260221-part3-domain-layer-extraction-inventory.md`
- `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`
- `docs/reports/20260221-full-legacy-retirement-migration-notes.md`
- `docs/planning/20260221-full-legacy-repo-retirement-roadmap.md`
- `docs/checklists/20260221-full-legacy-repo-retirement-checklist.md`
- `docs/checklists/20260221-final-manual-validation-runbook.md`
- `docs/reports/archive/`
- `docs/planning/archive/`
- `docs/checklists/archive/`

## Test Split
- Archived compatibility characterization tests: `python -m pytest -m legacy`
- Migration/cutover tests: `python -m pytest -m migration`
- Full suite: `python -m pytest`
