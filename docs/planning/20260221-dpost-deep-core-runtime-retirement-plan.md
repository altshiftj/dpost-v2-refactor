# dpost Deep-Core Runtime Retirement Plan

## Goal
- Retire remaining legacy deep-core runtime dependencies from canonical `dpost`
  runtime paths while preserving full behavior parity.
- Complete rehost ownership for processing, record lifecycle, sync
  orchestration, and config runtime surfaces to open-source-grade boundaries.

## Non-Goals
- No redesign of business behavior, plugin semantics, or user-facing workflows.
- No UI framework rewrite in this wave.
- No big-bang replacement of all legacy modules in one PR.

## Constraints
- Mandatory tests-first execution for each capability slice:
  red migration contract -> green implementation -> refactor -> full gates.
- Preserve current runtime behavior:
  startup, processing stage order, rejection handling, record persistence,
  immediate sync, and user-visible error messaging.
- Required quality gates per slice:
  - `python -m pytest tests/migration/<slice>.py`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`
- Architecture governance updates are mandatory in each architecture-impacting
  slice.

## Approach
- Use boundary-first strangler extraction from existing shim modules:
  - `src/dpost/application/runtime/runtime_dependencies.py`
  - `src/dpost/infrastructure/runtime/config_dependencies.py`
  - `src/dpost/infrastructure/sync/kadi.py`
- Extract by capability area, not by broad technical layer:
  1. processing
  2. records
  3. sync
  4. config runtime
- Keep each PR/slice narrowly scoped with explicit migration contracts.

## Milestones
1. Processing Core Rehost (P0) - status: completed
- Add migration contracts proving canonical processing paths no longer import
  `ipat_watchdog.core.processing` directly.
- Introduce dpost-owned processing models/services modules.
- Rehost orchestration from legacy `FileProcessManager` into dpost application
  processing services, preserving stage semantics.
- Reduce `runtime_dependencies.py` processing imports to zero.

2. Record Lifecycle Rehost (P1) - status: completed
- Add migration contracts for record manager ownership and side-effect parity.
- Introduce dpost-owned record lifecycle service and repository/port boundaries.
- Rehost record create/update/save/get and sync-trigger orchestration.
- Remove legacy record manager imports from canonical processing paths.

3. Sync Core Rehost (P1) - status: completed
- Add migration contracts for sync ownership and immediate-sync parity.
- Split Kadi behavior into dpost-owned sync service + Kadi infrastructure
  adapter modules.
- Preserve lazy optional dependency behavior and actionable error messages.
- Keep `SyncAdapterPort` authoritative in application paths.

4. Config Runtime Rehost (P2) - status: in progress
- Add migration contracts for config runtime service ownership.
- Introduce dpost-owned config runtime lifecycle module.
- Retire `config_dependencies.py` legacy imports when parity is green.

5. Boundary Shim Retirement + Import Sweep (P3) - status: pending
- Remove now-empty shim modules (`runtime_dependencies.py`,
  `config_dependencies.py`) after ownership migration is complete.
- Add final import-sweep migration contracts ensuring canonical runtime paths
  have no direct `ipat_watchdog.core.*` imports.

6. OSS Hardening and Contributor Surface Finalization (P4) - status: pending
- Finalize architecture docs with stable module boundaries.
- Add/refresh extension-point docs and contributor migration notes.
- Confirm glossary + ADR alignment for the final architecture state.

## Dependencies
- Existing migration test harness and CI quality gates.
- Stable local reproduction of integration and migration suites.
- Maintainer signoff for any boundary policy updates requiring ADR changes.

## Risks and Mitigations
- Risk: behavior drift in processing/retry/rejection timing.
  - Mitigation: characterization migration tests per stage boundary before
    implementation.
- Risk: sync behavior drift and user-visible error regressions.
  - Mitigation: explicit migration contracts for immediate-sync and error copy.
- Risk: oversized PRs reduce review quality.
  - Mitigation: one capability slice per PR with strict scope guardrails.
- Risk: hidden coupling discovered late.
  - Mitigation: enforce import boundary assertions in migration tests per slice.

## Test Plan
- Slice-level red/green:
  - `python -m pytest tests/migration/test_phaseXX_<slice>.py`
- Required gates each slice:
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`
- Parity focus areas:
  - processing stage sequence and retry policy
  - route/reject behavior and filesystem side effects
  - record persistence semantics
  - immediate-sync trigger and failure handling
  - startup/config initialization behavior

## Rollout / Validation
- Use small incremental PRs by milestone order.
- Update active docs (`reports`, `planning`, `checklists`, architecture docs,
  glossary) in each slice.
- Retire each shim only when:
  - slice migration contracts are green
  - full required gates are green
  - docs are synchronized
- Run manual operator checks after milestones P1, P3, and P4.

## Definition of Done
- Canonical runtime modules in `src/dpost` contain no direct
  `ipat_watchdog.core.*` imports except intentionally preserved UI implementation
  boundaries documented by policy.
- All required gates are green.
- Architecture baseline/contract/responsibility catalog and glossary reflect the
  final ownership state.
- Contributor-facing docs describe extension points and migration-complete
  runtime architecture clearly.
