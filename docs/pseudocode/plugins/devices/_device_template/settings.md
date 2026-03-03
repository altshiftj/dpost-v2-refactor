---
id: plugins/devices/_device_template/settings.py
origin_v1_files:
  - src/dpost/device_plugins/extr_haake/settings.py
  - src/dpost/device_plugins/erm_hioki/settings.py
  - src/dpost/device_plugins/rhe_kinexus/settings.py
  - src/dpost/device_plugins/test_device/settings.py
  - src/dpost/device_plugins/utm_zwick/settings.py
  - src/dpost/device_plugins/rmx_eirich_el1/settings.py
  - src/dpost/device_plugins/rmx_eirich_r01/settings.py
  - src/dpost/device_plugins/dsv_horiba/settings.py
  - src/dpost/device_plugins/sem_phenomxl2/settings.py
  - src/dpost/device_plugins/psa_horiba/settings.py
lane: Plugin-Device
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Device-specific typed settings and defaults.

## Origin Gist
- Source mapping: template derived from 10 device-plugin origin files.
- Legacy gist: Keeps device plugin module settings.py for extr_haake. Keeps device plugin module settings.py for erm_hioki. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Device-specific typed settings and defaults.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
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



