# Coverage-to-Refactor Insights Deep Dive (2026-02-21)

## Purpose

Translate coverage hardening outcomes into concrete refactor guidance that
reduces production risk, not just test percentages.

## Evidence Baseline

- Validation command:
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit`
- Latest result:
  - `537 passed, 1 skipped, 1 warning`
  - total coverage: `93%` (`4990 stmts, 341 miss`)

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
   - `CandidateMetadataPolicy` from `_derive_candidate_metadata`.
   - `RoutePolicy` from `_build_route_context` and `_rename_retry_policy_stage`.
   - `ForcePathPolicy` from `_post_persist_side_effects_stage`.
2. Keep `FileProcessManager` as orchestration shell only.
3. Add direct policy tests that do not require active global config/service.

Acceptance criteria:

- `file_process_manager.py` coverage increases with fewer integration-style tests.
- New policy modules have deterministic unit tests and no filesystem side effects.

## Insight 2: Hidden config globals still leak into deep infrastructure seams

Primary evidence:

- `src/dpost/infrastructure/sync/kadi_manager.py:22` reads separator via
  `_id_separator() -> current().id_separator`.
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

## Insight 5: Dynamic plugin loading remains a low-coverage reliability surface

Primary evidence:

- `src/dpost/plugins/system.py` still at `74%` with misses concentrated in
  entry-point loading, lazy import error paths, duplicate registration handling,
  and version-specific entry-point code.

Risk:

- Packaging or environment differences can break discovery silently.
- Startup behavior may differ between dev/prod environments.

Refactor action:

1. Introduce `PluginDiscoveryPort` and adapter for importlib/entry_points.
2. Unit-test loader logic against a deterministic fake discovery source.
3. Keep one integration test for real entry-point wiring.

Acceptance criteria:

- Most plugin loader tests stop monkeypatching importlib internals directly.
- Error messages for missing/invalid plugins are contract-tested.

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

1. `file_process_manager` policy extraction (highest ROI).
2. `kadi_manager` config/dynamic-client seam extraction.
3. `device_watchdog_app` lifecycle outcome decomposition.
4. `plugins/system` discovery adapter extraction.

## Cross-Reference

- Summary findings: `docs/reports/20260221-coverage-informed-architecture-findings.md`
- Execution checklist: `docs/checklists/20260221-coverage-hardening-action-items-checklist.md`
