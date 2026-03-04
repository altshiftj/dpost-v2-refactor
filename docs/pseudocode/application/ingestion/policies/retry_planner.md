---
id: application/ingestion/policies/retry_planner.py
origin_v1_files:
  - src/dpost/application/processing/rename_retry_policy.py
  - src/dpost/application/retry_delay_policy.py
  - src/dpost/application/runtime/retry_planner.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Shared retry delay calculation and retry-limit rules.

## Origin Gist
- Source mapping: `src/dpost/application/processing/rename_retry_policy.py`, `src/dpost/application/retry_delay_policy.py`, `src/dpost/application/runtime/retry_planner.py`.
- Legacy gist: Unifies retry policy in one planner module. Merges legacy retry delay policy into unified planner. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Merge, Move.
- Target responsibility: Shared retry delay calculation and retry-limit rules.
- Improvement goal: Consolidate duplicated logic into a single canonical owner. Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Retry policy settings (max attempts, base delay, max delay, backoff factor, jitter ratio).
- Current attempt index and failure classification.
- Optional deterministic jitter seed (event id / correlation id).
- Stage-specific retry overrides (for example persist vs stabilize behavior).

## Outputs
- `RetryPlan` model with terminal type (`retry` or `stop_retrying`), delay, and next attempt index.
- Cap-reached diagnostics and reason code.
- Helper functions for backoff and jitter calculations.
- Policy validation errors for invalid retry configuration.

## Invariants
- Attempt index is monotonic and non-negative.
- Delay values are non-negative and bounded by configured max delay.
- For fixed seed + inputs, jittered delay is deterministic.
- Planner is pure and side-effect free.

## Failure Modes
- Invalid retry config (negative delays, zero max attempts where forbidden) yields `RetryPlannerConfigError`.
- Invalid attempt index yields `RetryPlannerAttemptError`.
- Numeric overflow while computing backoff yields `RetryPlannerComputationError`.
- Missing required stage override metadata yields `RetryPlannerOverrideError`.

## Pseudocode
1. Validate retry policy configuration and current attempt index.
2. If attempt cap reached or failure class is non-retryable, return terminal `stop_retrying` plan.
3. Compute base delay using configured strategy (fixed/exponential) and stage overrides.
4. Apply bounded jitter derived from deterministic seed.
5. Clamp final delay to configured max and build `RetryPlan` with next attempt index.
6. Return retry plan and reason metadata used by engine and failure outcome policy.

## Tests To Implement
- unit: cap logic, backoff+jitter determinism, delay clamping, and invalid config handling.
- integration: stabilize/persist/engine failure paths use retry planner consistently to decide retry vs terminal outcomes.



