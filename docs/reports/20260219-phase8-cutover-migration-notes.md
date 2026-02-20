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
- Legacy compatibility entrypoint has been retired:
  - `src/ipat_watchdog/__main__.py` removed on `2026-02-20`
  - This was executed ahead of the previously announced sunset date
    (`2026-06-30`).

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
- Treat any remaining compatibility wording in docs/checklists as historical
  context only; canonical runtime behavior is now `dpost`-only.

## User Notes
- If you run from source, use `python -m dpost`.
- If you run installed console scripts, use `dpost`.
- `python -m ipat_watchdog` is no longer supported.
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
