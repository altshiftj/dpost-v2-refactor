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
- TBD

## Outputs
- TBD

## Invariants
- TBD

## Failure Modes
- TBD

## Pseudocode
1. TBD
2. TBD
3. TBD

## Tests To Implement
- unit: TBD
- integration: TBD



