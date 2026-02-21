# dpost Full Legacy Decoupling Clean-Architecture Roadmap

## Goal
- Fully retire runtime/application/plugin/config dependencies on
  `src/ipat_watchdog/core/...` and `src/ipat_watchdog/plugin_system.py` from
  canonical `dpost` startup and execution paths.
- Preserve functional behavior while reaching open-source-grade architecture
  quality: explicit boundaries, typed contracts, low coupling, and documented
  extension points.

## Non-Goals
- No broad feature expansion unrelated to legacy decoupling.
- No plugin behavior redesign unless required to preserve architecture
  boundaries or parity guarantees.
- No big-bang rewrite.

## Constraints
- Behavioral parity is mandatory for startup, processing, routing, record
  persistence, and sync error semantics.
- Existing markers and gate commands remain required:
  - `python -m pytest tests/migration/...`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`
- Architecture governance must stay aligned:
  - `docs/architecture/architecture-baseline.md`
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/responsibility-catalog.md`
  - `docs/architecture/adr/`

## Progress Snapshot (2026-02-21)
- Completed:
  - Native `dpost` bootstrap service implemented and transition bootstrap
    adapter retired.
  - Runtime app loop ownership rehosted into
    `src/dpost/application/runtime/device_watchdog_app.py`.
  - Runtime app/infrastructure dependency boundaries added to isolate legacy
    config/processing/session/storage imports from canonical runtime files:
    `src/dpost/infrastructure/runtime/desktop_ui.py`,
    `src/dpost/infrastructure/runtime/ui_adapters.py`.
  - Canonical plugin loading boundaries implemented in
    `src/dpost/plugins/loading.py` and `src/dpost/plugins/system.py`.
  - Canonical startup logging + observability paths moved to
    `dpost.infrastructure` modules.
  - Processing helper ownership rehosted under
    `src/dpost/application/processing/` and canonical processing manager imports
    decoupled from `ipat_watchdog.core.processing.*`.
  - Storage utility boundary rehosted under
    `src/dpost/infrastructure/storage/filesystem_utils.py` with dpost-boundary
    imports.
  - Config runtime lifecycle ownership rehosted under
    `src/dpost/application/config/` and dpost config boundary now avoids direct
    legacy imports.
  - Metrics registry ownership rehosted under
    `src/dpost/application/metrics.py` with registry-safe collector reuse.
  - Transition shim modules retired from canonical runtime path:
    `src/dpost/application/runtime/runtime_dependencies.py` and
    `src/dpost/infrastructure/runtime/config_dependencies.py`.
  - Desktop UI implementation rehosted under dpost runtime infrastructure:
    `src/dpost/infrastructure/runtime/tkinter_ui.py` and
    `src/dpost/infrastructure/runtime/dialogs.py`.
- In progress:
  - Retirement of remaining intentional legacy plugin compatibility seams
    (`dpost.plugins.system` hook namespace marker +
    `dpost.plugins.legacy_compat` fallback mappings).
- Next deep-core migration target:
  - Execute plugin-namespace compatibility retirement/import sweep after dpost
    plugin package migration criteria are satisfied.

## Deep-Core Planning Artifacts
- Detailed deep-core execution plan:
  - `docs/planning/20260221-dpost-deep-core-runtime-retirement-plan.md`
- Detailed deep-core execution checklist:
  - `docs/checklists/20260221-dpost-deep-core-runtime-retirement-checklist.md`
- Deep-core inventory baseline report:
  - `docs/reports/20260221-deep-core-runtime-retirement-inventory.md`

## Approach
- Use a capability-by-capability strangler model with explicit decoupling
  slices.
- For each slice, enforce this lifecycle:
  - add failing migration tests for the boundary contract
  - implement `dpost` native service/port/adapter path
  - run parity-focused migration and full suites
  - remove or narrow legacy adapter surface
  - update architecture/report/checklist docs in the same change set
- Keep composition root authoritative for dependency wiring.
- Require explicit ownership:
  - domain: pure rules/models
  - application: orchestration/use-cases/ports
  - infrastructure: adapters/integrations/runtime glue
  - plugins: extension implementations only

## Milestones
1. Capability Audit Freeze and Parity Baseline
- Expand migration contracts to map legacy capabilities to required `dpost`
  equivalents (startup, processing, plugins/config, records/sync, observability).
- Lock parity expectations in migration tests and inventory reports.

2. Native Runtime Bootstrap Replacement
- Replace `legacy_bootstrap_adapter` delegation with native `dpost` bootstrap
  implementation.
- Preserve startup settings/errors/context contract behavior.

3. Plugin and Config Ownership Migration
- Move plugin loader/discovery and PC-device mapping ownership to `dpost`
  boundaries.
- Move config runtime wiring ownership to `dpost` modules while preserving
  actionable startup error paths.

4. Application Runtime + Processing Rehost
- Rehost runtime loop orchestration and processing entrypoints from legacy core
  into `dpost/application`.
- Keep stage-order behavior and side-effect timing equivalent.

5. Records and Sync Core Migration
- Rehost record persistence contracts and sync trigger orchestration to
  `dpost` ports/adapters.
- Keep immediate-sync and failure-message semantics equivalent.

6. Legacy Retirement and OSS Hardening
- Remove residual canonical runtime dependencies on legacy core modules.
- Finalize public architecture docs, extension contracts, and contributor
  guidance for long-term open-source maintainability.

## Dependencies
- Stable migration CI gates and reproducible local test runs.
- Completion of parity test contracts for each decoupling slice.
- Maintainer review for architectural decisions with ADR updates as needed.

## Risks and Mitigations
- Risk: hidden runtime coupling appears late.
  - Mitigation: maintain capability-scoped inventories and boundary assertions.
- Risk: migration slices preserve tests but degrade readability.
  - Mitigation: require syntactic simplification evidence per slice.
- Risk: plugin ecosystem regressions.
  - Mitigation: keep discovery/actionability tests and representative plugin
    smoke checks in each relevant gate.
- Risk: behavioral drift under refactor.
  - Mitigation: preserve legacy characterization tests plus migration boundary
    checks before adapter retirement.

## Test Plan
- Required gates per slice:
  - `python -m pytest tests/migration/<slice-contract>.py`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`
- Parity emphasis areas:
  - startup error semantics and env resolution
  - runtime mode behavior (headless/desktop)
  - processing decision paths and retries
  - plugin discovery/load failures and hints
  - record persistence + sync side effects

## Rollout / Validation
- Execute in incremental PRs with one decoupling slice per change set.
- Keep active report/plan/checklist docs updated after each slice.
- Retire each legacy adapter only when:
  - parity contracts are green
  - migration/full gates are green
  - architecture docs are synchronized
- After retirement, run manual operator validation for desktop and headless
  runtime workflows before phase closure.
