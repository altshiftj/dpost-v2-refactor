# RPC: Application Processing Sprawl Posture and Reduction Strategy

## Date
- 2026-03-03

## Status
- Accepted

## Context
- `src/dpost/application/processing/` recently completed a wrapper-sprawl
  consolidation slice in the naming-settings migration wave.
- The current processing package now has many focused helper modules and a few
  larger orchestration hubs.
- The question for this RPC is whether current decomposition is healthy or has
  crossed into costly sprawl.

## Evidence Snapshot (Current Tree)
- Package size:
  - `25` Python modules
  - `2714` total lines
  - median module size: `73` lines
- Largest modules:
  - `src/dpost/application/processing/file_process_manager.py` (`443` lines)
  - `src/dpost/application/processing/device_resolver.py` (`339` lines)
  - `src/dpost/application/processing/processing_pipeline.py` (`276` lines)
  - `src/dpost/application/processing/stability_tracker.py` (`246` lines)
- Internal dependency fan-out:
  - `FileProcessManager`: `16` processing-module dependencies
  - `_ProcessingPipeline`: `9` processing-module dependencies
- Test surface:
  - `25` dedicated unit test modules under
    `tests/unit/application/processing/`
  - recent refactor checkpoints report stable full-suite green and preserved
    unit coverage for `src/dpost`.

## Assessment
- Healthy decomposition signals:
  - policy-only modules are small and deterministic
    (`rename_retry_policy`, `route_context_policy`, `force_path_policy`,
    `stability_timing_policy`).
  - side-effect sinks/emission helpers isolate IO and interaction concerns
    (`failure_emitter`, `immediate_sync_error_emitter`,
    `post_persist_bookkeeping`).
  - pipeline stages are explicit and testable (`processing_pipeline`,
    `processing_pipeline_runtime`).
- Sprawl risk signals:
  - cognitive navigation cost is high for common edits that cross several tiny
    modules.
  - `FileProcessManager` remains a high-coupling hub with broad collaborator
    knowledge and many stage helpers.
  - runtime adapter methods in `processing_pipeline_runtime` still proxy manager
    private methods, so contracts are spread across files.

## Decision
- Sprawl is **moderate but controlled** right now; this is not a crisis-level
  architecture failure.
- A broad package merge/rewrite is **not** recommended at this time.
- Reduction should be **trigger-based and slice-based**: only consolidate where
  evidence shows low-value indirection or repeated multi-file churn.

## Stop-Line (Do Not Refactor Past This Without New Evidence)
- No additional structural decomposition/consolidation should be started unless
  at least one trigger condition is observed in active work.
- A single module being "long" is not a sufficient trigger by itself.
- Wrapper extraction is allowed only when it provides one of:
  - explicit contract boundary used by another module (`Protocol`/port seam),
  - pure policy seam with dedicated tests,
  - side-effect sink boundary enabling deterministic testing.
- If none of the above apply, keep logic co-located to avoid new navigation
  sprawl.

## Current Posture Checkpoint
- As of 2026-03-03:
  - pipeline/runtime boundary (`ProcessingPipelineRuntimePort`) is in place;
  - low-value wrapper-only stages were already consolidated in
    `FileProcessManager` and `_ProcessingPipeline`;
  - remaining structure is considered acceptable operational complexity, not
    active sprawl debt.

## Trigger Conditions for Consolidation
- Trigger A:
  - one behavior change repeatedly touches `4+` helper modules in this package.
- Trigger B:
  - a helper module only forwards calls/data without independent policy,
    validation, or contract value.
- Trigger C:
  - `FileProcessManager` grows further in fan-out or responsibilities for
    another cross-cutting concern.

## Reduction Strategy (When Triggered)
1. Pipeline policy co-location (low risk)
- consolidate tightly-coupled, pipeline-only helper policies into one module
  when they change together (for example route/retry/unappendable prompt flow).
- keep functions pure and covered; reduce navigation hops.

2. Persistence side-effect coordinator extraction (medium risk)
- extract record-persistence and post-persist side-effect orchestration from
  `FileProcessManager` into an explicit collaborator owned by application layer.
- keep `FileProcessManager` focused on queue/runtime lifecycle and top-level
  orchestration.

3. Runtime adapter contract hardening (medium risk)
- reduce manager-private-method proxying by shifting runtime adapter calls to
  explicit collaborator interfaces where practical.
- preserve `ProcessingPipelineRuntimePort` as the pipeline contract boundary.

## Non-Goals
- no behavior changes to processing, routing, or sync semantics.
- no immediate large-scale file moves solely for aesthetic reorganization.
- no domain/infrastructure boundary rewrites in this slice.

## Acceptance Criteria
- Existing processing behavior remains unchanged (unit/integration green).
- Consolidation slices include focused red/green tests for each moved seam.
- Dependency direction remains compliant with
  `docs/architecture/architecture-contract.md`.
- Ownership updates are reflected in
  `docs/architecture/responsibility-catalog.md` when responsibilities shift.

## References
- `docs/reports/archive/20260302-naming-settings-sot-migration-baseline-report.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`
