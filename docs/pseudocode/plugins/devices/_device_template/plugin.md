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
- Plugin host lifecycle calls (`initialize`, `activate`, `shutdown`).
- Device plugin settings snapshot validated by template settings module.
- Runtime/profile context used for capability gating.
- Contract version metadata from `plugins/contracts`.

## Outputs
- Required plugin entry points:
  - `metadata()` returning stable plugin id/version/family metadata.
  - `capabilities()` returning explicit capability flags.
  - `create_processor(settings)` returning processor contract implementation.
  - `validate_settings(raw_settings)` returning typed validation result.
- Optional lifecycle hooks (`on_activate`, `on_shutdown`) with typed outcomes.
- Typed plugin-level errors for invalid metadata/capability/factory behavior.

## Invariants
- `metadata().plugin_id` is stable and globally unique.
- Capability flags are explicit booleans; implicit capabilities are forbidden.
- `create_processor` returns an object that satisfies processor contract.
- Required entry points must be exported by every device plugin implementation.

## Failure Modes
- Missing required entry point export raises `DevicePluginEntrypointError`.
- Invalid metadata shape/version raises `DevicePluginMetadataError`.
- Capability declaration mismatch raises `DevicePluginCapabilityError`.
- Processor factory failure or contract mismatch raises `DevicePluginProcessorFactoryError`.

## Pseudocode
1. Define required export functions (`metadata`, `capabilities`, `create_processor`, `validate_settings`).
2. Implement `metadata()` with stable plugin id, family=`device`, version, and supported profile tags.
3. Implement `capabilities()` returning explicit booleans for supported operations.
4. Implement `validate_settings(raw_settings)` delegating to typed settings module.
5. Implement `create_processor(settings)` that builds processor contract instance.
6. Optionally implement lifecycle hooks and return typed results to plugin host.

## Tests To Implement
- unit: required export presence, metadata/capability shape validation, and processor factory contract conformance.
- integration: plugin host discovers and activates a concrete device plugin built from this template and can create a processor through declared entry points.



