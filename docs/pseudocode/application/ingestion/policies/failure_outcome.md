---
id: application/ingestion/policies/failure_outcome.py
origin_v1_files:
  - src/dpost/application/processing/failure_outcome_policy.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Failure outcome model and normalization rules.

## Origin Gist
- Source mapping: `src/dpost/application/processing/failure_outcome_policy.py`.
- Legacy gist: Normalizes failure outcome types and handling.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Failure outcome model and normalization rules.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Error classification output from `error_handling` policy.
- Stage metadata and current retry attempt context.
- Retry planner decision (if retryable).
- Optional port/emission side-effect statuses for enriched failure context.

## Outputs
- Canonical `FailureOutcome` model with explicit terminal type (`retry`, `failed`, `rejected`).
- Retry payload (delay, next attempt index, cap-reached flag) when applicable.
- Human-readable and machine-readable reason fields.
- Conversion helpers from stage exceptions/results to failure outcomes.

## Invariants
- Every failure outcome includes stage id, reason code, severity, and terminal type.
- Terminal type set is closed and explicit (`retry`, `failed`, `rejected`).
- Retry payload is present only when terminal type is `retry`.
- Outcome normalization is pure and side-effect free.

## Failure Modes
- Missing required classification fields yields `FailureOutcomeValidationError`.
- Inconsistent retry payload (for example retry type without retry plan) yields `FailureOutcomeConsistencyError`.
- Unknown terminal type token yields `FailureOutcomeTypeError`.
- Overflow/invalid retry counters yield `FailureOutcomeRetryStateError`.

## Pseudocode
1. Accept normalized error classification and current processing retry context.
2. Determine terminal type based on classification + retry planner decision.
3. Build typed `FailureOutcome` object with required reason/severity/stage metadata.
4. Attach retry payload only when terminal type is `retry`.
5. Validate consistency of fields and raise typed errors for malformed combinations.
6. Expose conversion helper used by engine and failure emitter policies.

## Tests To Implement
- unit: terminal-type normalization, retry-payload consistency checks, and invalid outcome rejection.
- integration: engine failure paths produce stable `FailureOutcome` objects consumed by failure emitter and runtime app policies.



