# Phase 8 Migration Notes (Contributors and Users)

## Date
- 2026-02-19

## Audience
- Contributors maintaining or extending `dpost`.
- Operators/users launching runtime workflows from source or packaged builds.

## What Changed
- Canonical project/package identity is now `dpost`.
- Canonical startup commands are:
  - `python -m dpost`
  - `dpost`
- Legacy compatibility entrypoint remains temporarily at
  `src/ipat_watchdog/__main__.py` with explicit sunset date:
  - Sunset: `2026-06-30`

## Command Mapping
| Previous | Canonical Now |
|---|---|
| `python -m ipat_watchdog` | `python -m dpost` |
| `ipat-watchdog` | `dpost` |

## Contributor Notes
- Prefer `dpost` naming in docs, scripts, examples, and onboarding paths.
- Keep migration/cutover test coverage under `tests/migration/`.
- Avoid introducing new direct imports from `dpost` entry modules to
  `ipat_watchdog.core.app.bootstrap`; use `dpost.runtime.bootstrap` bridge
  utilities instead.
- Treat legacy compatibility paths as transition-only and remove them at/after
  the sunset window once validation gates are complete.

## User Notes
- If you run from source, use `python -m dpost`.
- If you run installed console scripts, use `dpost`.
- Existing environment variables (`PC_NAME`, `DEVICE_PLUGINS`,
  `PROMETHEUS_PORT`, `OBSERVABILITY_PORT`, `DPOST_*`) remain unchanged.
- Runtime mode behavior remains:
  - `DPOST_RUNTIME_MODE=headless` (default)
  - `DPOST_RUNTIME_MODE=desktop`

## Verification References
- Phase 8 cutover contract tests:
  `tests/migration/test_phase8_cutover_identity.py`
- Runtime mode parity checks:
  `tests/migration/test_runtime_mode_selection.py`
- Migration marker gate:
  `python -m pytest -m migration`
