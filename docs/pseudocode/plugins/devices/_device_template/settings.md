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
- Raw device plugin config payload from runtime settings tree.
- Device template default values.
- Validation schema constraints (types, ranges, required keys).
- Optional profile-based overrides.

## Outputs
- Typed `DevicePluginSettings` model.
- Normalized settings dictionary for processor/plugin construction.
- Validation result with field-level error codes.
- Redacted settings view for diagnostics/logging.

## Invariants
- Defaults are explicit and applied deterministically.
- Required keys are enforced before plugin activation.
- Unknown keys are either rejected or explicitly tracked by policy.
- Settings model is immutable after validation.

## Failure Modes
- Missing required key raises `DevicePluginSettingsMissingKeyError`.
- Invalid type/range/value raises `DevicePluginSettingsValidationError`.
- Unknown key under strict mode raises `DevicePluginSettingsUnknownKeyError`.
- Profile override conflict raises `DevicePluginSettingsOverrideError`.

## Pseudocode
1. Define typed settings schema with defaults and required fields.
2. Merge raw settings with defaults and profile overrides by precedence.
3. Validate merged values against schema type/range constraints.
4. Normalize canonical values (paths/tokens) needed by processor/plugin modules.
5. Build immutable `DevicePluginSettings` and redacted diagnostics view.
6. Return typed validation errors for invalid or conflicting settings.

## Tests To Implement
- unit: default application, required key validation, strict unknown-key handling, and override precedence.
- integration: device plugin template validates settings before host activation and passes typed settings into processor factory.



