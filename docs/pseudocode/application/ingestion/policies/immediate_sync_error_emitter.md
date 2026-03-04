---
id: application/ingestion/policies/immediate_sync_error_emitter.py
origin_v1_files:
  - src/dpost/application/processing/immediate_sync_error_emitter.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Emit immediate-sync failure outcomes consistently.

## Origin Gist
- Source mapping: `src/dpost/application/processing/immediate_sync_error_emitter.py`.
- Legacy gist: Isolates immediate sync error emission behavior.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Emit immediate-sync failure outcomes consistently.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Immediate sync attempt result/error from post-persist stage.
- Persisted record metadata and correlation context.
- Failure outcome + failure emitter policy helpers.
- Sync escalation settings (severity overrides, alert toggles).

## Outputs
- Normalized immediate-sync `FailureOutcome`.
- Emission result from delegated failure emitter.
- Optional unsynced bookkeeping command for records service.
- Sync escalation marker for runtime/UI notifications.

## Invariants
- Policy is invoked only for immediate sync attempt failures.
- Generated outcome uses dedicated reason code namespace for sync errors.
- For one event id, immediate sync failure is emitted at most once.
- Module does not schedule retries directly; retry planning remains in retry planner policy.

## Failure Modes
- Missing required sync error metadata yields `ImmediateSyncErrorInputError`.
- Failure outcome normalization failure yields `ImmediateSyncOutcomeError`.
- Underlying failure emitter port error yields `ImmediateSyncEmissionError`.
- Missing persisted record reference when required yields `ImmediateSyncRecordReferenceError`.

## Pseudocode
1. Accept sync error result plus record/context metadata from post-persist stage.
2. Normalize sync error into immediate-sync-specific failure classification.
3. Build canonical `FailureOutcome` using failure outcome policy helpers.
4. Delegate emission to failure emitter and capture emission result.
5. Return combined immediate-sync failure package with optional unsynced bookkeeping hint.
6. Mark escalation flag when sync error severity crosses configured threshold.

## Tests To Implement
- unit: immediate-sync reason code normalization, once-per-event emission guard, and emitter error mapping.
- integration: post-persist immediate sync failures generate consistent outcomes/events and preserve unsynced record state.



