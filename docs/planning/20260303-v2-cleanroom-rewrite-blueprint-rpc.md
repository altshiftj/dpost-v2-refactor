# RPC: V2 Clean-Room Rewrite Blueprint (Intent-Driven)

## Date
- 2026-03-03

## Status
- Hypothetical Blueprint (Not Approved for Execution)

## Context
- This document defines what a full "start from square one" rewrite would look like if we optimized for long-term clarity and explicit boundaries.
- It is a planning artifact, not an active migration plan.
- Existing guidance still applies:
  - `docs/planning/20260303-legacy-seams-freshness-rpc.md` says full rewrite is not currently warranted.

## Goal
- Rebuild the runtime around explicit contracts and deterministic behavior while preserving functional intent of the current system.

## Why This Exists
- This is a preparedness artifact: if incremental cleanup stops being cost-effective, we already have an execution-ready rewrite posture.
- It prevents "panic architecture" by defining target boundaries and a safe migration shape ahead of time.

## Non-Goals
- No big-bang cutover.
- No loss of existing operational behavior (routing, naming, persistence, sync semantics).
- No implicit compatibility layers in production flow.

## Design Principles
1. Contracts first.
- Every cross-boundary dependency is a typed port/protocol.

2. Explicit context only.
- No ambient runtime globals in production pathways.

3. Pure stage logic.
- Decisions are pure functions where practical; side effects are injected.

4. Progressive cutover.
- V2 is verified in parallel against V1 outputs before replacement.

## V2 Module Shape (Proposed)
```text
src/dpost_v2/
  domain/
    naming/
    routing/
    records/
    processing/
  application/
    contracts/
      context.py
      ports.py
      plugin_contracts.py
      events.py
    ingestion/
      engine.py
      stages/
        resolve.py
        stabilize.py
        preprocess.py
        route.py
        persist.py
        post_persist.py
    records/
      service.py
    startup/
      settings.py
      resolver.py
      bootstrap.py
  infrastructure/
    runtime/
      ui/
      observer/
    storage/
      record_store.py
      file_ops.py
    sync/
      noop.py
      kadi.py
    observability/
      metrics.py
      tracing.py
  plugins/
    host.py
    discovery.py
    validators.py
    contracts.py
```

## Core Contracts (Proposed)
1. `RuntimeContext`
- Immutable runtime context object containing naming, paths, watcher policy, device identity, and session settings.

2. `IngestionStage`
- `run(input, context, services) -> StageResult`
- `StageResult` supports `defer`, `reject`, `accept(next_input)`, and optional retry hints.

3. `RecordStorePort`
- Transactional record operations (`get/create/update/mark_unsynced/save`) with atomicity guarantees.

4. `SyncPort`
- Backend-agnostic sync contract returning structured outcomes.

5. `PluginCapabilityContract`
- Explicit plugin capabilities (`can_handle`, `preprocess`, `process`, optional `batch`) plus manifest metadata.

## Data and Persistence Strategy
- Move persistence from ad-hoc JSON update patterns to a transactional record store (SQLite recommended) with explicit schema and migrations.
- Keep export/import tool for JSON compatibility during migration period.

## Observability Strategy
- Stage-level structured events with correlation IDs.
- Unified metrics dimensions by stage/result/device.
- Error taxonomy with stable codes for operator-facing diagnostics.

## Test Strategy (Rewrite-Grade)
1. Behavior capture harness (pre-rewrite):
- Golden fixtures for filenames, routing outcomes, record persistence transitions, and sync outcomes.

2. Contract tests:
- Stage contract tests for each stage input/output shape.
- Plugin contract validation tests.

3. Differential parity tests:
- Replay same input corpus through V1 and V2, compare outputs and side effects.

4. Cutover safety tests:
- Startup/profile/runtime mode matrix tests.
- Failure injection tests (missing files, permission errors, sync failures).

## 4-Phase Delivery Plan
1. Phase 1: Spec and Harness
- Freeze functional intent via executable golden specs.
- Build parity corpus and assertion tooling.

2. Phase 2: Kernel and Contracts
- Implement `RuntimeContext`, stage contracts, ports, and plugin host validators.
- Stand up minimal no-op end-to-end vertical slice.

3. Phase 3: Adapter and Behavior Port
- Implement storage, sync, runtime adapters and stage implementations.
- Continuously run differential parity tests against V1.

4. Phase 4: Shadow, Cutover, Retirement
- Run V2 in shadow mode.
- Promote to active runtime when parity and reliability gates pass.
- Retire V1 pathways with rollback guard window.

## First 30 Days (If Activated)
1. Week 1
- Lock rewrite charter and freeze parity corpus scope.
- Ship behavior-capture harness against current V1.

2. Week 2
- Land `RuntimeContext`, stage/result contracts, and no-op stage runner.
- Add contract-test skeletons for all stage interfaces.

3. Week 3
- Implement storage and sync port adapters with fake backends for deterministic tests.
- Start first parity replay lane in CI (subset corpus).

4. Week 4
- Port one complete vertical slice (`resolve -> route -> persist`) and compare outputs vs V1.
- Publish first parity dashboard and gap backlog.

## Risks and Mitigations
1. Hidden behavior loss
- Mitigation: exhaustive behavior-capture harness before implementation.

2. Scope explosion
- Mitigation: strict contract boundaries and phased milestones.

3. Operational disruption
- Mitigation: shadow mode and reversible cutover gate.

## Success Gates
- Differential parity pass rate >= 99.9% on agreed corpus.
- No unresolved severity-1 regressions in startup, processing, persistence, or sync.
- Operator-visible behavior and artifacts match agreed intent.
- Performance envelope within acceptable variance from V1 baseline.

## Decision Trigger for Activating This Plan
- Only execute if maintainability metrics or architecture risks cross threshold where incremental freshness slices no longer provide acceptable ROI.

## Activation Guardrails
- Require explicit ADR approval before Phase 1 execution.
- Keep V1 as source of operational truth until parity gates are satisfied.
- No destructive cutover without a tested rollback path and 1 full release cycle of shadow confidence.

## References
- `docs/planning/20260303-legacy-seams-freshness-rpc.md`
- `docs/planning/20260303-processing-sprawl-posture-rpc.md`
- `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`
- `docs/planning/20260303-v2-cloud-agent-week1-roadmap.md`
- `docs/reports/20260303-v2-cloud-agent-week1-feasibility-report.md`
- `docs/checklists/20260303-v2-cloud-agent-week1-execution-checklist.md`
