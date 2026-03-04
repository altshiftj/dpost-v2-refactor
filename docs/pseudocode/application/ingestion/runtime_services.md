---
id: application/ingestion/runtime_services.py
origin_v1_files:
  - src/dpost/application/processing/processing_pipeline_runtime.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Side-effect facade consumed by stage machine (fs/io/sync/ui/event ports).

## Origin Gist
- Source mapping: `src/dpost/application/processing/processing_pipeline_runtime.py`.
- Legacy gist: Defines runtime service facade used by stage machine.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Side-effect facade consumed by stage machine (fs/io/sync/ui/event ports).
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Port bindings (`FileOpsPort`, `RecordStorePort`, `SyncPort`, `UiPort`, `EventPort`, `ClockPort`).
- Stage execution requests (read, move, persist, mark-unsynced, emit-event, trigger-sync).
- Correlation context used to annotate side-effect operations.
- Retry/cancellation metadata from ingestion policies.

## Outputs
- Unified runtime service methods with typed request/response envelopes.
- Normalized adapter errors mapped to ingestion policy-compatible error classes.
- Side-effect diagnostics metadata (duration, adapter id, operation outcome).
- No-op safe operations for disabled capabilities (for example sync disabled mode).

## Invariants
- Runtime services perform no domain decisions; they only execute requested side effects.
- Every method includes correlation metadata propagation.
- Adapter exceptions are normalized before they leave the facade.
- Idempotency expectations for operations are explicit in method contracts.

## Failure Modes
- Adapter timeout/cancellation maps to `RuntimeServiceTimeoutError`/`RuntimeServiceCancelledError`.
- Adapter contract mismatch maps to `RuntimeServiceContractError`.
- Unavailable optional capability returns typed no-op/disabled outcome, not raw exception.
- Unexpected adapter exceptions map to `RuntimeServiceUnexpectedError`.

## Pseudocode
1. Define `RuntimeServices` facade initialized with required port bindings and adapter metadata.
2. Implement facade methods (`read_source`, `move_to_target`, `save_record`, `emit_event`, `trigger_sync`, `now`) as thin wrappers.
3. Wrap each adapter call with correlation propagation and standardized timing capture.
4. Normalize adapter exceptions into contract-defined runtime service errors.
5. Return typed result envelopes consumed by stages and policies.
6. Expose `is_capability_enabled` helpers for stage decisions without leaking adapter implementations.

## Tests To Implement
- unit: error normalization across all wrapped ports, correlation propagation, and disabled-capability behavior.
- integration: ingestion stages use runtime services facade to perform file/record/sync/event side effects with consistent typed outcomes.



