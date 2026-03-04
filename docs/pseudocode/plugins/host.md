---
id: plugins/host.py
origin_v1_files:
  - src/dpost/plugins/system.py
lane: Plugin-Host
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Plugin runtime host, capability lookup, and lifecycle control.

## Origin Gist
- Source mapping: `src/dpost/plugins/system.py`.
- Legacy gist: Renames plugin system to host lifecycle module.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Plugin runtime host, capability lookup, and lifecycle control.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Discovered plugin descriptors from discovery module.
- Plugin contract validator and plugin-facing contract aliases.
- Runtime lifecycle signals (`initialize`, `activate_profile`, `shutdown`).
- Settings/profile context needed for plugin activation.

## Outputs
- Registered plugin host state with active/inactive plugin instances.
- Capability lookup API (`get_device_plugins`, `get_pc_plugins`, `get_by_capability`).
- Plugin lifecycle operation results and diagnostics.
- Typed host errors for registration/activation failures.

## Invariants
- Plugin ids are unique within host registry.
- Plugin must pass contract validation before registration.
- Host controls lifecycle transitions; plugins are not activated implicitly.
- Capability lookup results are deterministic for same registry/profile state.

## Failure Modes
- Duplicate plugin id registration raises `PluginHostDuplicateIdError`.
- Contract validation failure raises `PluginHostContractError`.
- Plugin initialization/activation failure raises `PluginHostActivationError`.
- Shutdown hook failure raises `PluginHostShutdownError`.

## Pseudocode
1. Initialize empty plugin registry and lifecycle state maps.
2. Register discovered plugins after validating contract exports and metadata.
3. Activate plugins based on selected profile and capability requirements.
4. Serve capability lookup queries using registry metadata snapshots.
5. Route plugin lifecycle events (`initialize`, `reload`, `shutdown`) through host-controlled hooks.
6. Return typed results/errors for each lifecycle operation.

## Tests To Implement
- unit: duplicate-id rejection, contract validation gating, capability lookup determinism, and lifecycle transitions.
- integration: discovery + catalog + host activation flows register and run template plugins for selected profiles with clean shutdown behavior.



