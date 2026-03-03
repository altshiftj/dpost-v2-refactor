---
id: application/ingestion/processor_factory.py
origin_v1_files:
  - src/dpost/application/processing/processor_factory.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Select and instantiate processor from plugin registry + context.

## Origin Gist
- Source mapping: `src/dpost/application/processing/processor_factory.py`.
- Legacy gist: Selects processor implementation from plugin contracts.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Select and instantiate processor from plugin registry + context.
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



