---
id: application/records/service.py
origin_v1_files:
  - src/dpost/application/records/record_manager.py
lane: Records-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Record lifecycle API (`create`, `update`, `mark_unsynced`, `save`) via record port.

## Origin Gist
- Source mapping: `src/dpost/application/records/record_manager.py`.
- Legacy gist: Defines records service over explicit store contract.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Record lifecycle API (`create`, `update`, `mark_unsynced`, `save`) via record port.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
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



