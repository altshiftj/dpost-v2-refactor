# 20260305 V2 Handshake Slice 03: PC Policy Scope and Runtime Enforcement

## Scope
- Complete the `Plugin policy handshake (PC scope first)` section from the handshake-first checklist.
- Keep the slice focused on workstation selection, host-resolved device scope, and runtime enforcement.
- Do not yet wire PC-owned sync payload shaping or full processor `prepare/process` handoff.

## TDD Record
- Red tests added first in `tests/dpost_v2/application/startup/test_settings_schema.py`:
  - `test_schema_accepts_optional_plugin_policy_block`
- Red tests added first in `tests/dpost_v2/application/startup/test_settings_service.py`:
  - `test_settings_service_reads_plugin_policy_from_environment`
- Red tests added first in `tests/dpost_v2/plugins/test_host.py`:
  - `test_host_resolves_pc_scoped_device_plugins_from_pc_settings`
- Red tests added first in `tests/dpost_v2/runtime/test_composition.py`:
  - `test_composition_exposes_selected_pc_scope_in_diagnostics`
  - `test_composition_runtime_rejects_candidate_outside_selected_pc_scope`
  - `test_composition_runtime_selects_allowed_device_with_selected_pc_scope`
- Initial failure mode before implementation:
  - startup settings had no explicit workstation policy field
  - settings service had no environment path for workstation selection
  - plugin host had no API to derive allowed device scope from PC plugin settings
  - runtime processor selection always iterated all active device plugins

## Implementation
- `src/dpost_v2/application/startup/settings_schema.py`
  - Added optional `plugins` block support:
    - `pc_name`
    - `device_plugins`
  - Normalized plugin ids to lowercase tokens.
- `src/dpost_v2/application/startup/settings.py`
  - Added `PluginPolicySettings`.
  - Extended `StartupSettings` and `to_dependency_payload()` with the plugin-policy block.
- `src/dpost_v2/application/startup/settings_service.py`
  - Added default environment source loading for:
    - `DPOST_PC_NAME`, then `PC_NAME`
    - `DPOST_DEVICE_PLUGINS`, then `DEVICE_PLUGINS`
  - Kept source precedence stable:
    - defaults -> file -> environment -> cli
- `src/dpost_v2/plugins/host.py`
  - Added `PcDeviceScope`.
  - Added `resolve_device_scope_for_pc(...)` to derive allowed device ids from the selected PC plugin's validated settings.
  - Scope resolution intersects configured `active_device_plugins` with the currently active device plugins for the selected profile.
- `src/dpost_v2/runtime/composition.py`
  - Added runtime plugin-policy resolution from startup settings.
  - Added composition diagnostics:
    - `selected_pc_plugin`
    - `scoped_device_plugins`
    - `pc_scope_applied`
  - Runtime processor selection now enforces the scoped device list when a workstation PC is explicitly selected.
  - Out-of-scope files now reject deterministically at resolve instead of falling through to unrelated device plugins.

## Validation
- `python -m pytest -q tests/dpost_v2/application/startup/test_settings_schema.py tests/dpost_v2/application/startup/test_settings_service.py tests/dpost_v2/plugins/test_host.py tests/dpost_v2/runtime/test_composition.py`
  - `40 passed`
- `python -m pytest -q tests/dpost_v2/application/startup tests/dpost_v2/runtime tests/dpost_v2/plugins`
  - `101 passed`
- `python -m pytest -q tests/dpost_v2`
  - `403 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed

## Result
- V2 now has an explicit workstation-selection handshake:
  - config/settings path via `plugins.pc_name`
  - environment path via `DPOST_PC_NAME` with legacy `PC_NAME` fallback
- Runtime can now enforce:
  - `horiba_blb -> psa_horiba, dsv_horiba`
  - `tischrem_blb -> sem_phenomxl2`
  - `zwick_blb -> utm_zwick`
- Composition diagnostics expose the selected workstation and scoped device set for review/debugging.

## Compatibility Decision
- This slice does not force a workstation selection for all headless runs.
- If no `plugins.pc_name` or `DPOST_PC_NAME`/`PC_NAME` is provided, runtime keeps the existing profile-wide device selection behavior.
- Reason:
  - the architecture seam is now explicit and test-covered
  - existing standalone/generic probes are not silently broken mid-checklist
  - a later slice can still choose to hard-require workstation selection once operator/config posture is ready

## Deferred
- PC-owned sync payload shaping in post-persist
- Explicit processor `prepare/process` handoff in ingestion stages
- Decision on whether headless standalone should eventually fail fast when no workstation PC is declared
