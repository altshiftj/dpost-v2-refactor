# dpost Migration Execution Board

## Board Metadata
- Created: 2026-02-18
- Planning horizon: 2026-02-18 to 2026-05-15
- Runtime posture: headless-first
- Sync posture: optional adapter model

## Owner Roles
- Core Owner: Repository maintainer driving architecture and merges.
- Plugin Owner: Maintainer handling plugin hygiene and discovery validation.
- Runtime Owner: Maintainer handling entrypoints, runtime modes, and deployment scripts.
- QA Owner: Maintainer handling gates, regression checks, and manual validation.

## Schedule
| Phase | Window (Start -> Target End) | Owner | Status | Gate to Close |
|---|---|---|---|---|
| Phase 1: Baseline and Contract Freeze | 2026-02-19 -> 2026-02-26 | QA Owner + Core Owner | Completed (2026-02-18) | Baseline tests green and architecture contract doc linked |
| Phase 2: dpost Spine and Headless Composition Root | 2026-02-27 -> 2026-03-10 | Runtime Owner + Core Owner | Completed (2026-02-18) | Headless `dpost` entrypoint smoke test green, legacy entrypoint intact |
| Phase 3: Framework Kernel and Sync Adapter Contract | 2026-03-11 -> 2026-03-19 | Core Owner | Completed (2026-02-18) | Framework contracts + reference implementations green before concrete adapter migration |
| Phase 4: Configuration Consolidation | 2026-03-20 -> 2026-03-31 | Core Owner | Planned | Legacy constant fallbacks removed from operational paths |
| Phase 5: Processing Pipeline Decomposition | 2026-04-01 -> 2026-04-15 | Core Owner | Planned | Stage services extracted, integration suite unchanged/green |
| Phase 6: Plugin and Discovery Hardening | 2026-04-16 -> 2026-04-24 | Plugin Owner | Planned | Plugin inventory normalized and discovery tests green |
| Phase 7: Desktop Runtime Integration | 2026-04-27 -> 2026-05-06 | Runtime Owner | Planned | Desktop and headless smoke tests both green |
| Phase 8: Final Cutover and Cleanup | 2026-05-07 -> 2026-05-15 | Core Owner + QA Owner | Planned | `dpost` canonical metadata/docs complete and release gate passed |

## Weekly Cadence
- Monday: phase planning and risk review.
- Wednesday: mid-phase checkpoint against gate criteria.
- Friday: gate readiness check and issue triage.
- Friday (documentation gate): verify baseline/responsibility/ADR/glossary updates for the week.

## Change Control
- Any scope change that affects a closed phase gate requires:
- explicit note in this board
- updated acceptance criteria in the phase checklist
- re-baselined target end date

## Current State (as of 2026-02-18)
- Decisions captured and locked in planning/checklist docs.
- Phase 1 gate formally closed on 2026-02-18:
- `python -m pytest -m legacy`: `288 passed, 4 skipped, 4 deselected`.
- `python -m pytest -m migration`: `4 passed, 292 deselected`.
- Contract linkage verified from `docs/architecture/README.md` to `docs/architecture/architecture-contract.md`.
- Phase 2 gate closed early on 2026-02-18:
- `src/dpost/` package skeleton exists.
- `dpost` script entrypoint exists in `pyproject.toml`.
- migration entrypoint tests exist under `tests/migration/`.
- marker split is active (`legacy` and `migration`).
- Sequencing update: Phase 3 is framework-first; concrete Kadi adapter migration follows kernel contract validation.
- Phase 3 tests-first kickoff on 2026-02-18:
- added `tests/migration/test_sync_adapter_selection.py` to lock initial kernel
  expectations for sync adapter selection/error handling.
- initial red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `3 failed` before implementation.
- post-approval implementation status:
- added `src/dpost/application/ports/sync.py` (`SyncAdapterPort`),
  `src/dpost/infrastructure/sync/noop.py` (`NoopSyncAdapter`), and
  adapter selection in `src/dpost/runtime/composition.py`.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `3 passed`.
- migration marker check:
  `python -m pytest -m migration`
  returned `7 passed, 292 deselected`.
- Phase 3 startup-wiring tests-first increment on 2026-02-18:
- added failing tests for `compose_bootstrap` sync-factory wiring and
  unknown-adapter env behavior in
  `tests/migration/test_sync_adapter_selection.py`.
- added failing test for `dpost.main()` unknown-adapter env exit path in
  `tests/migration/test_dpost_main.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  returned `3 failed, 7 passed` pending implementation.
- startup-wiring implementation status:
- `src/dpost/runtime/composition.py` now pre-validates selected adapter and
  passes `sync_manager_factory` into legacy bootstrap.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  returned `10 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `10 passed, 292 deselected`.
- Phase 3 Kadi adapter tests-first increment on 2026-02-18:
- added failing tests for `DPOST_SYNC_ADAPTER=kadi` startup wiring and missing
  optional dependency error handling in
  `tests/migration/test_sync_adapter_selection.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `2 failed, 5 passed` pending implementation.
- Kadi adapter implementation status:
- added `src/dpost/infrastructure/sync/kadi.py` and updated
  `src/dpost/runtime/composition.py` to select `kadi` explicitly.
- missing optional dependency (`kadi_apy`) now raises startup error on adapter
  selection.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `7 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `12 passed, 292 deselected`.
- Phase 3 optional Kadi packaging tests-first increment on 2026-02-18:
- added migration assertions for default/noop startup behavior when Kadi
  dependency is unavailable and explicit `kadi` startup failure messaging in
  `tests/migration/test_sync_adapter_selection.py`.
- added packaging contract coverage in
  `tests/migration/test_optional_kadi_packaging.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py`
  returned `1 failed, 9 passed` pending implementation.
- optional Kadi packaging implementation status:
- `pyproject.toml` now keeps `kadi-apy` out of default
  `[project].dependencies` and exposes it through
  `[project.optional-dependencies].kadi`.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py tests/migration/test_dpost_main.py`
  returned `15 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `15 passed, 292 deselected`.
- Phase 3 reference plugin flow tests-first increment on 2026-02-18:
- added failing migration test in
  `tests/migration/test_reference_plugin_flow.py` to assert
  `DPOST_PLUGIN_PROFILE=reference` startup wiring through composition.
- red-state verification:
  `python -m pytest tests/migration/test_reference_plugin_flow.py`
  returned `1 failed` pending implementation.
- framework kernel boundary + reference plugin flow implementation status:
- added `src/dpost/plugins/reference.py` and updated
  `src/dpost/runtime/composition.py` to support `DPOST_PLUGIN_PROFILE` with
  explicit `reference` profile mapping.
- updated architecture boundary documentation in:
  `docs/architecture/architecture-contract.md`,
  `docs/architecture/architecture-baseline.md`,
  `docs/architecture/responsibility-catalog.md`, and `GLOSSARY.csv`.
- green verification:
  `python -m pytest -m migration`
  returned `16 passed, 292 deselected`.
- Phase 3 gate closed on 2026-02-18 after kernel contracts, reference sync
  adapter, and reference plugin flow were validated together.
