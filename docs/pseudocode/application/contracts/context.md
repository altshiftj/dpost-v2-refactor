---
id: application/contracts/context.py
origin_v1_files:
  - src/dpost/application/processing/processor_runtime_context.py
lane: Contracts-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Immutable `RuntimeContext`, `ProcessingContext`, context constructors/validators.

## Origin Gist
- Source mapping: `src/dpost/application/processing/processor_runtime_context.py`.
- Legacy gist: Moves runtime context model into shared contract module.

## V2 Improvement Intent
- Transform posture: Merge.
- Target responsibility: Immutable `RuntimeContext`, `ProcessingContext`, context constructors/validators.
- Improvement goal: Consolidate duplicated logic into a single canonical owner.
## Inputs
- Startup settings snapshot (mode, profile, naming policy knobs, retry policy knobs).
- Runtime dependency identifiers (clock source id, ui adapter id, sync adapter id).
- Per-file processing facts (source path, observed event type, observed timestamp, optional force-path hint).
- Correlation data (session id, event id, trace id) passed from runtime orchestration.

## Outputs
- `RuntimeContext` immutable value object used for app/session lifecycle logic.
- `ProcessingContext` immutable value object used for a single ingestion attempt.
- Constructor and clone helpers (`from_settings`, `for_candidate`, `with_retry`, `with_failure`).
- Validation helpers that return normalized contexts or typed validation errors.

## Invariants
- Context instances are immutable after construction.
- `ProcessingContext.runtime_context` always points to the originating `RuntimeContext`.
- `session_id`, `event_id`, and `trace_id` are non-empty strings.
- Retry counters are monotonic and cannot decrease between derived contexts.
- Force-path overrides are normalized once and cannot be mutated by downstream stages.

## Failure Modes
- Missing required startup fields yields `ContextValidationError` during `from_settings`.
- Invalid mode/profile combination yields `UnsupportedRuntimeModeError`.
- Invalid path token in per-file context yields `InvalidCandidateContextError`.
- Retry derivation with negative delay or attempt index yields `RetryStateError`.

## Pseudocode
1. Define frozen dataclasses for `RuntimeContext` and `ProcessingContext` with explicit typed fields.
2. Implement `RuntimeContext.from_settings(settings, dependency_ids)` that validates required fields and normalizes mode/profile tokens.
3. Implement `ProcessingContext.for_candidate(runtime_context, candidate_event)` that captures event metadata and initializes retry state.
4. Implement pure clone helpers (`with_retry`, `with_failure`, `with_route`) that return new instances and preserve immutable source fields.
5. Add `validate_runtime_context` and `validate_processing_context` helpers used by startup bootstrap and ingestion engine entrypoints.
6. Ensure all validation failures are mapped to typed contract-level errors, not infrastructure exceptions.

## Tests To Implement
- unit: construction rejects missing ids, immutability is enforced, and retry clone helpers preserve invariant fields.
- integration: startup bootstrap emits a valid `RuntimeContext`, ingestion engine derives `ProcessingContext` instances without ambient global state.



