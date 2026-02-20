# dpost Phase 9-13 Full Strangler Continuation Plan

## Goal
- Complete the migration from transitional `dpost` composition-over-legacy
  runtime wiring to a native `dpost` runtime architecture with legacy runtime
  dependency fully retired.

## Non-Goals
- No broad feature expansion outside migration boundary extraction.
- No behavior-changing plugin rewrites unless required by boundary migration.
- No one-shot rewrite; all changes remain phase-gated and incremental.

## Constraints
- Preserve existing runtime behavior through characterization and migration
  tests at each phase gate.
- Maintain architecture-contract layering (domain/application/infrastructure/
  plugins) and composition-root wiring discipline.
- Keep compatibility retirement sequencing aligned with sunset constraints and
  human validation gates.

## Approach
- Continue strangler migration in five additional phases after Phase 8:
  - Phase 9: native `dpost` bootstrap core boundary.
  - Phase 10: application orchestration extraction.
  - Phase 11: infrastructure adapter extraction.
  - Phase 12: plugin/config boundary migration.
  - Phase 13: final legacy package runtime retirement.
- Use tests-first increments per phase:
  - add failing migration tests
  - approve contract
  - implement to green
  - verify with marker/full gates

## Phase 9: Native dpost Bootstrap Core
- Scope:
  - remove runtime delegation dependency on
    `ipat_watchdog.core.app.bootstrap` from `dpost` composition/bootstrap
    boundaries.
  - establish native `dpost` bootstrap context/settings/error contract.
- Acceptance criteria:
  - `src/dpost/runtime/bootstrap.py` contains no legacy bootstrap-module path
    dependency.
  - `src/dpost/runtime/composition.py` contains no legacy bootstrap type/module
    dependency.
  - migration tests for native bootstrap boundary are green.

## Phase 10: Application Orchestration Extraction
- Scope:
  - move core orchestration seams currently hosted in legacy processing/runtime
    modules into `dpost/application` services and ports.
  - keep behavior parity with current processing flow contracts.
- Acceptance criteria:
  - orchestration entrypoints used by runtime composition resolve through
    `dpost/application`.
  - migration and legacy characterization tests remain green.

## Phase 11: Infrastructure Adapter Extraction
- Scope:
  - move filesystem/observability/runtime glue integrations behind explicit
    `dpost/infrastructure` adapters and ports.
  - keep application layer depending on ports only.
- Acceptance criteria:
  - application modules have no direct dependency on concrete legacy
    infrastructure modules.
  - adapter selection/wiring remains composition-root owned.

## Phase 12: Plugin and Config Boundary Migration
- Scope:
  - migrate plugin discovery/config ownership toward `dpost` boundaries while
    preserving plugin behavior contracts.
  - remove remaining transition-only plugin/config coupling.
- Acceptance criteria:
  - plugin/config contracts for runtime startup are resolved through `dpost`
    boundaries.
  - discovery and startup error messaging remains actionable and tested.

## Phase 13: Legacy Runtime Retirement
- Scope:
  - remove remaining runtime dependencies on `src/ipat_watchdog/core/...` from
    canonical runtime path.
  - retain only historical documentation references as needed.
- Acceptance criteria:
  - canonical runtime startup path is fully `dpost`-native.
  - post-retirement migration gate passes (lint, format, migration marker,
    full suite, manual checks).

## Dependencies
- Phase 8 manual checks and sunset-driven compatibility retirement tasks.
- Maintainer approval for each phase-gate transition.
- Ongoing updates to architecture baseline/contract/responsibility docs.

## Risks and Mitigations
- Risk: hidden legacy coupling surfaces emerge late.
  - Mitigation: phase-specific inventory reports plus targeted migration tests.
- Risk: behavior drift while extracting orchestration/infrastructure seams.
  - Mitigation: tests-first increments with marker/full regression gates.
- Risk: plugin integration regressions from boundary shifts.
  - Mitigation: plugin discovery/actionability and representative plugin flow
    checks in each relevant phase.

## Test Plan
- Phase gates should include:
  - `python -m pytest tests/migration/<phase-specific-file>.py`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`

## Rollout / Validation
- Execute each phase via dedicated report + plan + checklist docs.
- Keep execution board status updates at each increment boundary.
- Close each phase only when acceptance criteria, test gates, and manual
  validation expectations are satisfied.
