---
id: plugins/devices/_device_template/processor.py
origin_v1_files:
  - src/dpost/device_plugins/dsv_horiba/file_processor.py
  - src/dpost/device_plugins/psa_horiba/file_processor.py
  - src/dpost/device_plugins/rmx_eirich_r01/file_processor.py
  - src/dpost/device_plugins/extr_haake/file_processor.py
  - src/dpost/device_plugins/utm_zwick/file_processor.py
  - src/dpost/device_plugins/test_device/file_processor.py
  - src/dpost/device_plugins/sem_phenomxl2/file_processor.py
  - src/dpost/device_plugins/erm_hioki/file_processor.py
  - src/dpost/device_plugins/rhe_kinexus/file_processor.py
  - src/dpost/device_plugins/rmx_eirich_el1/file_processor.py
lane: Plugin-Device
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Device-specific parsing, preprocessing, and candidate derivation logic.

## Origin Gist
- Source mapping: template derived from 10 device-plugin origin files.
- Legacy gist: Keeps device processing logic for dsv_horiba with consistent processor naming. Keeps device processing logic for psa_horiba with consistent processor naming. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Device-specific parsing, preprocessing, and candidate derivation logic.
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



