# Full Legacy Repo Retirement Roadmap

## Goal
- Retire the remaining legacy repository surface under `src/ipat_watchdog/**`
  and converge the project on canonical `dpost` ownership for runtime,
  plugins, tests, and contributor documentation.

## Scope
- In scope:
  - source retirement for legacy package trees
  - migration of legacy-targeted tests/fixtures to canonical dpost ownership
  - packaging and entrypoint cleanup
  - architecture and contributor documentation finalization
- Out of scope:
  - unrelated feature work
  - behavior redesign beyond parity-preserving refactor
  - large one-shot rewrites

## Current Starting Point (2026-02-21)
- Canonical `dpost` runtime decoupling is complete for Phase 9-13.
- Remaining work is repository-wide legacy retirement:
  - `src/ipat_watchdog/**/*.py`: `119` files
  - `ipat_watchdog` references in `tests/**`: `307`
- Inventory source:
  - `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`
- Kickoff progress:
  - migration guard test added:
    `tests/migration/test_full_legacy_repo_retirement_harness.py`
  - shared helper decoupling landed for:
    `tests/helpers/fake_ui.py`, `tests/helpers/fake_sync.py`, and
    `tests/helpers/fake_process_manager.py`

## End-State Definition
- `dpost` is the only canonical runtime/import target.
- No required production path depends on `src/ipat_watchdog/**`.
- Legacy test suite is either:
  - fully migrated to canonical dpost imports/contracts, or
  - intentionally archived with explicit non-gating status and rationale.
- Architecture/docs/testing guidance is canonical-dpost only.

## Execution Principles
- Tests-first slices (red -> green -> refactor) for behavior-affecting changes.
- Preserve behavior parity for startup, processing, routing, record persistence,
  sync side effects, and operator-visible errors.
- Keep changes incremental and checkpoint-committed.
- Update docs/governance artifacts in the same change set as architecture work.

## Phase Plan
1. Retirement Baseline Freeze
- Lock inventory and target state.
- Add migration guards for global retirement criteria.

2. Test Harness Canonicalization
- Migrate shared test fixtures/helpers from legacy imports to dpost boundaries.
- Remove `ipat_watchdog` imports from migration tests first, then unit/
  integration/manual tests.

3. Plugin Surface Retirement
- Ensure all plugin tests and loading paths resolve through `src/dpost/**`.
- Retire `src/ipat_watchdog/device_plugins/**` and
  `src/ipat_watchdog/pc_plugins/**` in bounded slices.

4. Core Runtime Surface Retirement
- Retire remaining legacy core modules (`core/app`, `core/processing`,
  `core/records`, `core/sync`, `core/config`, `core/storage`, `core/ui`)
  after test ownership is migrated.

5. Packaging and Entrypoint Cleanup
- Remove legacy package metadata references and stale naming hints.
- Keep only canonical script/module startup targets.

6. Documentation and OSS Hardening
- Finalize architecture baseline/contract/responsibility/ADR alignment.
- Finalize contributor docs for extension/testing/runtime workflows.
- Publish migration notes for downstream users.

7. Final Deletion Sweep and Validation
- Remove any residual dead compatibility artifacts.
- Run full required gates + manual validation checklist.
- Capture closure report with residual risk set to zero or explicit exceptions.

## Required Gates (Each Slice)
- `python -m pytest tests/migration/<slice>.py`
- `python -m pytest -m migration`
- `python -m ruff check .`
- `python -m black --check .`
- `python -m pytest`

## Risks and Mitigations
- Risk: hidden legacy coupling in tests.
  - Mitigation: import-sweep guards and fixture-by-fixture migration.
- Risk: behavior drift while deleting legacy modules.
  - Mitigation: red/green parity tests for each deleted capability slice.
- Risk: contributor confusion during transition.
  - Mitigation: keep roadmap/checklist/report and developer docs synchronized.

## Rollout
- Execute as checkpointed autonomous slices.
- Keep progress evidence in:
  - `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`
  - `docs/reports/20260221-phase10-13-runtime-boundary-progress.md`
  - new retirement progress reports as slices land.
