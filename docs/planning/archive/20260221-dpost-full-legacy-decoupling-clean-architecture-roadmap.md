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
  - Added canonical dpost processing helper modules for staged/batched plugin
    flows:
    `src/dpost/application/processing/batch_models.py`,
    `src/dpost/application/processing/staging_utils.py`,
    `src/dpost/application/processing/text_utils.py`.
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
  - Reference plugin packages migrated to canonical dpost namespaces:
    `src/dpost/device_plugins/test_device/` and
    `src/dpost/pc_plugins/test_pc/`.
  - Concrete device plugins migrated to canonical dpost namespace:
    `src/dpost/device_plugins/utm_zwick/` and
    `src/dpost/device_plugins/extr_haake/` and
    `src/dpost/device_plugins/erm_hioki/` and
    `src/dpost/device_plugins/sem_phenomxl2/` and
    `src/dpost/device_plugins/rmx_eirich_el1/` and
    `src/dpost/device_plugins/rmx_eirich_r01/` and
    `src/dpost/device_plugins/dsv_horiba/` and
    `src/dpost/device_plugins/rhe_kinexus/` and
    `src/dpost/device_plugins/psa_horiba/`.
  - Concrete PC plugins migrated to canonical dpost namespace:
    `src/dpost/pc_plugins/zwick_blb/` and
    `src/dpost/pc_plugins/haake_blb/` and
    `src/dpost/pc_plugins/hioki_blb/` and
    `src/dpost/pc_plugins/tischrem_blb/` and
    `src/dpost/pc_plugins/eirich_blb/` and
    `src/dpost/pc_plugins/horiba_blb/` and
    `src/dpost/pc_plugins/kinexus_blb/`.
  - Legacy plugin compatibility seams retired from canonical dpost paths:
    `src/dpost/plugins/legacy_compat.py` removed and
    `src/dpost/plugins/system.py` now canonical-only for dpost hook/namespace
    loading.
  - Records/sync parity hardening completed for immediate-sync behavior and
    user-visible sync failure surfacing via
    `tests/migration/test_phase13_records_sync_parity.py` and
    `src/dpost/application/processing/file_process_manager.py`.
  - Transition-only dpost processing helper
    (`_ProcessingPipeline._prepare_request`) retired and migration assertions
    now enforce no `ipat_watchdog` namespace literals in `src/dpost/**`.
  - Public extension contracts finalized in
    `docs/architecture/extension-contracts.md` with ADR governance in
    `docs/architecture/adr/ADR-0003-canonical-extension-contracts-and-legacy-namespace-retirement.md`.
- In progress:
  - Legacy package retirement planning for `src/ipat_watchdog/device_plugins/`
  and `src/ipat_watchdog/pc_plugins/` now that canonical dpost plugin
  packages are complete.
- Next deep-core migration target:
  - Execute legacy package deprecation and cleanup plan while preserving test
    parity and contributor migration guidance.
  - Active repo-wide retirement planning now tracked in:
    - `docs/reports/archive/20260221-full-legacy-repo-retirement-inventory.md`
    - `docs/planning/archive/20260221-full-legacy-repo-retirement-roadmap.md`
    - `docs/checklists/archive/20260221-full-legacy-repo-retirement-checklist.md`

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

