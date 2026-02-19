# Post-Sunset Compatibility Retirement Plan

## Goal
- Retire transition-only `ipat_watchdog` compatibility paths safely after the
  announced sunset date (`2026-06-30`) while preserving canonical `dpost`
  runtime behavior.

## Non-Goals
- Re-architecting non-compatibility legacy runtime internals in the same
  change set.
- Reformatting broad legacy areas unrelated to compatibility retirement.
- Altering stable plugin/business behavior outside compatibility path removal.

## Constraints
- Compatibility removal starts only after `2026-06-30`.
- Keep changes incremental and reviewable with migration tests green at each
  increment.
- Preserve Phase 8 tracking artifacts and update completion notes as each step
  lands.
- Keep manual operator validation explicit for desktop and headless workflows.

## Approach
- Use a three-wave retirement sequence:
1. Remove CLI compatibility surface.
2. Remove transition-only bootstrap bridge indirection.
3. Remove transition references in tests/docs/manual-check items.

### File-By-File Retirement Sequence
| Path | Planned Action (post-sunset) | Rationale |
|---|---|---|
| `src/ipat_watchdog/__main__.py` | Delete file. | Compatibility CLI entrypoint sunset reached. |
| `src/dpost/runtime/bootstrap.py` | Remove transition-only dynamic exception-class helpers (`startup_error_cls`, `missing_configuration_cls`) and simplify exports to non-transition runtime contract. | Bridge no longer needs to preserve dual-module exception monkeypatch behavior for compatibility path parity. |
| `src/dpost/__main__.py` | Simplify exception imports/catching to post-sunset runtime contract (remove compatibility alias wiring). | Remove transition glue once legacy entrypoint is gone. |
| `tests/migration/test_phase8_cutover_identity.py` | Update legacy-entrypoint guard to require file absence (not deprecation notice). | Move from transition acceptance to post-sunset enforcement. |
| `docs/checklists/20260218-dpost-architecture-tightening-checklist.md` | Remove transition-only manual parity step referencing `python -m ipat_watchdog`. | Post-sunset, legacy entrypoint parity is no longer applicable. |
| `docs/reports/20260219-phase8-cutover-migration-notes.md` | Replace transition wording with completed-retirement wording and historical mapping note. | Keep contributor/user guidance current. |
| `src/ipat_watchdog/plugin_system.py` | Replace remaining install hint string `pip install ipat-watchdog[...]` with `pip install dpost[...]`. | Remove residual legacy package naming from operator error guidance. |

## Milestones
- M1 (Sunset readiness): confirm date threshold reached and manual checks from
  Phase 8 are complete.
- M2 (Code retirement): remove legacy entrypoint and simplify bridge/main.
- M3 (Docs/tests cleanup): align migration tests, notes, and checklist/manual
  steps to post-sunset state.
- M4 (Gate close): full lint/test gate + final Phase 8 checklist close.

## Dependencies
- Human confirmation that sunset date (`2026-06-30`) has passed and release
  management approved removal window.
- Maintainer availability for manual desktop/headless validation.

## Risks and Mitigations
- Risk: hidden operational dependency on `python -m ipat_watchdog`.
  Mitigation: manual transition checks before retirement + explicit release
  notes callout.
- Risk: test brittleness from bootstrap exception class identity changes.
  Mitigation: migrate tests in same increment as bridge simplification and run
  `tests/migration/test_dpost_main.py` + `tests/migration/test_runtime_mode_selection.py`.
- Risk: stale docs/scripts after removal.
  Mitigation: run focused grep audit for `ipat-watchdog` and
  `python -m ipat_watchdog` before merge.

## Test Plan
- Focused migration tests:
  - `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  - `python -m pytest tests/migration/test_dpost_main.py`
  - `python -m pytest tests/migration/test_runtime_mode_selection.py`
  - `python -m pytest tests/migration/test_sync_adapter_selection.py`
- Gate checks:
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`

## Rollout / Validation
- Announce a final transition reminder before removal merge.
- Merge compatibility retirement as a dedicated PR tied to this plan/checklist.
- Confirm manual checks for desktop/headless runtime after merge.
- Mark Phase 8 compatibility-removal item complete in the architecture
  tightening checklist and execution board.
- Use the companion PR package:
  `docs/planning/20260219-post-sunset-compatibility-retirement-pr-runbook.md`.
