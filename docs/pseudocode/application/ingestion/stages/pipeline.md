---
id: application/ingestion/stages/pipeline.py
origin_v1_files:
  - src/dpost/application/processing/processing_pipeline.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Pure stage sequencing logic and stage transition rules.

## Origin Gist
- Source mapping: `src/dpost/application/processing/processing_pipeline.py`.
- Legacy gist: Stage machine remains explicit and independently testable.

## V2 Improvement Intent
- Transform posture: Split.
- Target responsibility: Pure stage sequencing logic and stage transition rules.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership.
## Inputs
- Initial pipeline state containing candidate context and correlation metadata.
- Stage handler map keyed by stage id.
- Transition policy table describing allowed next states for each stage outcome.
- Cancellation signal and max-stage-steps guard.

## Outputs
- Terminal pipeline result carrying final stage id and terminal outcome kind.
- Ordered stage transition log used by engine tracing.
- Intermediate state snapshots returned to engine for policy hooks.
- Typed pipeline errors for invalid transitions or missing stage handlers.

## Invariants
- Transition graph is acyclic for one pipeline run.
- Every non-terminal stage produces exactly one next-stage directive.
- Terminal result type is one of: `completed`, `retry`, `rejected`, `failed`.
- Pipeline runner is pure orchestration and performs no side effects itself.

## Failure Modes
- Missing stage handler for required stage yields `PipelineMissingStageError`.
- Invalid transition directive yields `PipelineTransitionError`.
- Exceeding max-step guard yields `PipelineCycleGuardError`.
- Cancellation signal yields deterministic terminal `failed`/`retry` outcome per policy.

## Pseudocode
1. Initialize current stage to `resolve` and create empty transition log.
2. Invoke current stage handler with immutable state and capture `StageResult`.
3. Validate result against transition table and derive next stage or terminal outcome.
4. Append transition record and update state snapshot if stage emitted enriched state.
5. Repeat until terminal outcome or cancellation/max-step guard is triggered.
6. Return terminal pipeline result and transition log to ingestion engine.

## Tests To Implement
- unit: transition-table enforcement, missing-stage detection, terminal outcome typing, and cycle-guard behavior.
- integration: engine + pipeline + all stage handlers execute full happy-path and failure-path transitions without side effects in pipeline module itself.



