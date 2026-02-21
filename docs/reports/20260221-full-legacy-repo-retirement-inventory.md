# Full Legacy Repo Retirement Inventory

## Date
- 2026-02-21

## Goal
- Establish a concrete baseline for retiring the remaining legacy repository
  surface under `src/ipat_watchdog/**` while preserving functional parity.

## Baseline Snapshot
- Legacy source files:
  - `src/ipat_watchdog/**` files: `615`
  - `src/ipat_watchdog/**/*.py` files: `119`
  - `src/ipat_watchdog/core/**/*.py`: `46`
  - `src/ipat_watchdog/device_plugins/**/*.py`: `42`
  - `src/ipat_watchdog/pc_plugins/**/*.py`: `26`
- Legacy references:
  - `ipat_watchdog` references in `src/**`: `307`
  - `ipat_watchdog` references in `tests/**`: `307`
  - `ipat_watchdog` references in `docs/**`: `277`
- Test estate:
  - `tests/unit/**/*.py`: `61`
  - `tests/integration/**/*.py`: `8`
  - `tests/manual/**/*.py`: `2`

## Existing Documentation Coverage
- Strong coverage exists for canonical runtime decoupling through Phase 9-13:
  - `docs/planning/20260221-dpost-full-legacy-decoupling-clean-architecture-roadmap.md`
  - `docs/checklists/20260221-dpost-full-legacy-decoupling-clean-architecture-checklist.md`
  - `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`
- Existing docs do not yet provide a full, end-to-end retirement execution plan
  for deleting the legacy package tree and migrating legacy test ownership.

## Gap Assessment
- Missing explicit end-state criteria for:
  - retiring `src/ipat_watchdog/core/**`
  - retiring `src/ipat_watchdog/device_plugins/**`
  - retiring `src/ipat_watchdog/pc_plugins/**`
  - retiring legacy-targeted test imports and fixtures.
- Missing phased plan that coordinates:
  - source retirement
  - test migration
  - packaging/entrypoint cleanup
  - contributor docs and release communication.

## Retirement Target State
- Canonical runtime, plugins, and extension contracts live under `src/dpost/**`.
- No runtime or test-critical dependency on `src/ipat_watchdog/**`.
- Legacy package tree is removed (or reduced to intentionally scoped stubs with
  explicit retirement date, if required temporarily).
- Architecture/testing docs and contributor docs describe only canonical dpost
  flows.

## Companion Artifacts
- Roadmap:
  - `docs/planning/20260221-full-legacy-repo-retirement-roadmap.md`
- Checklist:
  - `docs/checklists/20260221-full-legacy-repo-retirement-checklist.md`
