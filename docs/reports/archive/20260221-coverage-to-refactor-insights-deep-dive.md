# Coverage-to-Refactor Insights Deep Dive (2026-02-21)

## Purpose

Translate coverage hardening outcomes into concrete refactor guidance that
reduces production risk, not just test percentages.

## Evidence Baseline

- Validation command:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Latest result:
  - `666 passed, 1 skipped, 1 warning`
  - total coverage: `100%` (`5105 stmts, 0 miss`)

## Insight 1: Orchestration hotspots are carrying too many responsibilities

Primary evidence:

- `src/dpost/application/processing/file_process_manager.py`
  combines resolution, stability waiting, preprocessing, routing policy, rename
  loop policy, persistence, metrics, exception routing, and sync behavior in one
  class cluster (`_ProcessingPipeline` + `FileProcessManager`).

Risk:

- Hard-to-predict behavior drift when changing one concern (for example, rename
  flow behavior affecting sync/metrics/error behavior).
- High mocking burden in tests indicates missing seams.

Refactor action:

1. Extract pure policy units:
   - `CandidateMetadataPolicy` from `_derive_candidate_metadata`. (completed)
   - `ForcePathPolicy` from `_post_persist_side_effects_stage`. (completed)
   - `RoutePolicy` from `_build_route_context`. (remaining)
   - `RenameRetryPolicy` from `_rename_retry_policy_stage`. (completed)
   - `FailureOutcomePolicy` from `_handle_processing_failure` target/rejection classification. (expanded/completed seam)
2. Keep `FileProcessManager` as orchestration shell only.
3. Add direct policy tests that do not require active global config/service.

Acceptance criteria:

- `file_process_manager.py` coverage increases with fewer integration-style tests.
- New policy modules have deterministic unit tests and no filesystem side effects.

Current status:

- `file_process_manager.py` is now at `100%`.
- extracted policy modules (`candidate_metadata.py`, `force_path_policy.py`,
  `rename_retry_policy.py`, `route_context_policy.py`, `failure_outcome_policy.py`) are at `100%`.
- remaining work is route-context/failure-outcome structuring and dependency
  cleanup refactors (not coverage-driven).

## Insight 2: Hidden config globals still leak into deep infrastructure seams

Primary evidence:

- `src/dpost/infrastructure/sync/kadi_manager.py:22` reads separator via
  explicit resolver seam (improved), but other helpers still rely on ambient config.
- `src/dpost/application/processing/file_process_manager.py:341` defaults to
  `get_service()` when `config_service` is not passed.

Risk:

- Runtime behavior depends on ambient activation state and startup order.
- Failing tests can be caused by missing config context rather than functional
  logic.

Refactor action:

1. Inject naming/config dependencies explicitly at composition boundaries.
2. Replace `current()` lookups in deep functions with explicit parameters.
3. Keep fallback `get_service()` only at top-level runtime bootstrap.

Acceptance criteria:

- Deep helpers run in tests without implicit `activate_device` context.
- `kadi_manager` no longer imports runtime global config accessor.

Current status:

- `kadi_manager` now uses explicit separator and db-manager factory seams and
  is fully unit covered.
- `filesystem_utils` path/persistence helpers now accept explicit context
  parameters while preserving legacy signatures.
- `session_manager` timeout scheduling now supports an explicit provider seam.
- Kinexus/PSA sequence helpers now support explicit/lazy separator resolution
  with safe fallback when runtime config is unavailable.
- `application.naming.policy` wrappers now accept explicit context parameters,
  reducing monkeypatch pressure in callers/tests.
- remaining global-context cleanup is concentrated in residual storage/runtime
  helpers and any compatibility wrappers still reading ambient config directly.

## Insight 3: Retry and deferral policy is fragmented across layers

Primary evidence:

- Resolver delay behavior:
  `src/dpost/application/processing/device_resolver.py:147` and `:158`.
- App-level retry fallback:
  `src/dpost/application/runtime/device_watchdog_app.py:274`.

Risk:

- Divergent retry semantics between resolver deferrals and app queue retries.
- Harder operational tuning because delay policy is split by module.

Refactor action:

1. Introduce shared `RetryPolicy` value object in application layer.
2. Make resolver and watchdog consume this policy instead of hardcoded defaults.
3. Add tests for policy-driven backoff and lower-bound clipping.

Acceptance criteria:

- One source of truth for default delay, min delay, and invalid-value fallback.
- App/resolver tests validate identical behavior for the same policy config.

## Insight 4: Failure handling mixes side effects with control flow

Primary evidence:

- `file_process_manager` error paths move files, emit metrics, and queue rejections
  in the same branch (`_handle_processing_failure`, `_reject_immediately`,
  `_post_persist_side_effects_stage`).
- `device_watchdog_app` exception path mutates metrics, UI, and shutdown flow
  in a single method (`handle_exception`).

Risk:

- Failures become hard to reason about and to replay deterministically.
- Partial side-effect completion can leave inconsistent operational state.

Refactor action:

1. Emit structured failure outcomes/events from processing layer.
2. Handle UI/metrics/observer shutdown in outer orchestration boundary.
3. Preserve user-visible behavior through contract tests before migration.

Acceptance criteria:

- Domain/application methods return structured outcomes without direct UI calls.
- UI adapters consume outcomes and render notifications separately.

## Insight 5: Coverage exposed processor design pressure more than raw risk gaps

Primary evidence:

- previously low-covered processor modules are now fully covered with focused
  branch suites:
  - `src/dpost/device_plugins/erm_hioki/file_processor.py`
  - `src/dpost/device_plugins/utm_zwick/file_processor.py`
  - `src/dpost/device_plugins/psa_horiba/file_processor.py`
  - `src/dpost/device_plugins/rhe_kinexus/file_processor.py`
- no current global coverage misses remain; recent residual defensive path in
  `file_process_manager` is now explicitly documented/classified.

Risk:

- Raw coverage gaps are no longer the main problem; the next risk is
  maintainability of large processor/orchestrator methods with many side effects.
- Continued feature work in these modules can reintroduce coverage loss if seam
  extraction does not continue.

Refactor action:

1. Extract pure parse/normalization helpers from large processors into
   dedicated policy modules (now justified by test pain, not lack of coverage).
2. Preserve the new branch suites as regression harnesses while reducing test
   setup burden through helper seam extraction.
3. Keep lightweight integration tests for end-to-end processor contracts.

Acceptance criteria:

- Processor-specific helpers are testable without filesystem orchestration setup.
- Coverage remains stable while refactor slices continue, with any future
  defensive exclusions explicitly justified.

## Insight 6: Testability improved where boundaries are explicit

Primary evidence:

- Near/full coverage in runtime composition and UI adapter boundaries:
  - `src/dpost/runtime/composition.py`
  - `src/dpost/runtime/startup_config.py`
  - `src/dpost/infrastructure/runtime/ui_adapters.py`
  - `src/dpost/infrastructure/runtime/tkinter_ui.py`

Interpretation:

- The project’s architecture direction is validated by test economics:
  explicit ports and adapters were materially easier to verify and maintain.

Action:

- Continue refactor strategy that moves side effects to infrastructure adapters
  and preserves pure policy logic in application/domain layers.

## Prioritized Refactor Queue

1. `file_process_manager` failure emission boundary refinement
   (outcome construction vs emission stages split and sink injection completed; next candidate is post-persist sync-error UI/log boundary extraction).
2. global config access reduction in deep helper layers (continue after
   `filesystem_utils` explicit-context support).
3. retry policy unification across resolver/watchdog flows (shared retry-delay
   policy seam completed; next step is configuration centralization).
4. continue monitoring test naming/import hygiene as suites expand
   (guard test now enforces pytest import-key uniqueness).

## Cross-Reference

- Summary findings: `docs/reports/20260221-coverage-informed-architecture-findings.md`
- Execution checklist: `docs/checklists/20260221-coverage-hardening-action-items-checklist.md`
