# Phase 7 Desktop Runtime Integration Inventory

## Date
- 2026-02-19

## Context
- Phase 6 is closed and green.
- Phase 7 starts with an inventory-first pass and tests-first runtime-mode
  contract before desktop runtime wiring implementation.

## Inventory Scope
- Runtime composition and startup entrypoint wiring:
  - `src/dpost/runtime/composition.py`
  - `src/dpost/__main__.py`
- Legacy bootstrap runtime stack:
  - `src/ipat_watchdog/core/app/bootstrap.py`
  - `src/ipat_watchdog/core/ui/`
- Existing migration startup smoke coverage:
  - `tests/migration/test_dpost_main.py`

## Findings
| Area | Observation | Evidence |
|---|---|---|
| Runtime mode selection contract | Architecture contract requires runtime mode selection at composition root, but `dpost` composition does not yet expose runtime mode selection. | `docs/architecture/architecture-contract.md` and `src/dpost/runtime/composition.py` |
| Headless mode explicitness | Headless-first posture is documented, but startup wiring does not yet include an explicit runtime mode selector (`headless` vs `desktop`). | `docs/planning/20260218-dpost-architecture-tightening-plan.md` and `src/dpost/runtime/composition.py` |
| Desktop default coupling | Legacy bootstrap currently defaults UI creation to `TKinterUI` when no factory is passed, so runtime behavior is desktop-coupled by default. | `src/ipat_watchdog/core/app/bootstrap.py` (`bootstrap(..., ui_factory=TKinterUI, ...)`) |
| Migration smoke coverage gap | Existing `dpost` migration smoke tests validate success/failure control flow, but do not lock dual runtime-mode startup expectations. | `tests/migration/test_dpost_main.py` |

## Phase 7 Tests-First Contract Added
- Added migration tests in:
  - `tests/migration/test_runtime_mode_selection.py`
- New failing expectations cover:
  - explicit runtime mode resolver behavior (`headless` default, unknown-mode
    fail-fast)
  - explicit composition wiring of `ui_factory` for both `headless` and
    `desktop` modes
  - dual runtime-mode startup smoke expectations through `dpost.main()`
    with mode-specific composition wiring

## Red-State Verification
- `python -m pytest tests/migration/test_runtime_mode_selection.py`
  -> `6 failed`
- `python -m pytest -m migration`
  -> `6 failed, 63 passed, 302 deselected`

## Risks
- Until explicit runtime mode selection is implemented, desktop behavior remains
  implicit and headless path behavior can drift.
- Without dual-mode smoke checks, regressions can hide in entrypoint wiring and
  only surface in manual checks.

## Open Questions
- Should runtime mode selection be environment-only, or also support explicit
  function arguments for direct composition calls?
  - Answer: Deferred to implementation increment; tests currently lock env-driven
    selection behavior.

## Update Addendum (2026-02-19)
- Implemented first runtime integration increment and moved tests to green by:
  - adding explicit runtime mode resolver in
    `src/dpost/runtime/composition.py` with `DPOST_RUNTIME_MODE` support
    (`headless` default, `desktop` optional) and unknown-mode fail-fast errors
  - wiring explicit `ui_factory` selection in composition for both runtime
    modes
  - adding `src/dpost/infrastructure/runtime/headless_ui.py` for non-interactive
    headless runtime UI/scheduler behavior
- Verification after implementation:
  - `python -m pytest tests/migration/test_runtime_mode_selection.py`
    -> `6 passed`
  - `python -m pytest -m migration`
    -> `69 passed, 302 deselected`
- Implemented desktop parity characterization increment by:
  - extending `tests/migration/test_runtime_mode_selection.py` with desktop-mode
    bootstrap context wiring assertions and adapter behavior delegation checks
    (`UiInteractionAdapter` + `UiTaskScheduler`) using a desktop UI probe
- Implemented runtime mode behavior documentation increment by:
  - updating `README.md` with `DPOST_RUNTIME_MODE` mode selection details and
    related migration startup environment variables
- Verification after characterization/docs increment:
  - `python -m pytest tests/migration/test_runtime_mode_selection.py`
    -> `8 passed`
  - `python -m pytest -m migration`
    -> `71 passed, 302 deselected`
