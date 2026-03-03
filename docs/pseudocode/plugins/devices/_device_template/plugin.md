---
id: plugins/devices/_device_template/plugin.py
origin_v1_files:
  - src/dpost/device_plugins/rmx_eirich_el1/plugin.py
  - src/dpost/device_plugins/utm_zwick/plugin.py
  - src/dpost/device_plugins/psa_horiba/plugin.py
  - src/dpost/device_plugins/rhe_kinexus/plugin.py
  - src/dpost/device_plugins/test_device/plugin.py
  - src/dpost/device_plugins/erm_hioki/plugin.py
  - src/dpost/device_plugins/rmx_eirich_r01/plugin.py
  - src/dpost/device_plugins/dsv_horiba/plugin.py
  - src/dpost/device_plugins/extr_haake/plugin.py
  - src/dpost/device_plugins/sem_phenomxl2/plugin.py
lane: Plugin-Device
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Device plugin adapter exposing capability and processor factory hooks.

## Origin Gist
- Source mapping: template derived from 10 device-plugin origin files.
- Legacy gist: Keeps device plugin module plugin.py for rmx_eirich_el1. Keeps device plugin module plugin.py for utm_zwick. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Device plugin adapter exposing capability and processor factory hooks.
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



