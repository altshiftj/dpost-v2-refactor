---
id: application/ingestion/stages/resolve.py
origin_v1_files:
  - src/dpost/application/processing/device_resolver.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Resolve device/plugin and create candidate metadata.

## Origin Gist
- Source mapping: `src/dpost/application/processing/device_resolver.py`.
- Legacy gist: Owns resolve stage for device and plugin matching.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Resolve device/plugin and create candidate metadata.
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



