---
id: plugins/pcs/_pc_template/plugin.py
origin_v1_files:
  - src/dpost/pc_plugins/kinexus_blb/plugin.py
  - src/dpost/pc_plugins/eirich_blb/plugin.py
  - src/dpost/pc_plugins/horiba_blb/plugin.py
  - src/dpost/pc_plugins/hioki_blb/plugin.py
  - src/dpost/pc_plugins/test_pc/plugin.py
  - src/dpost/pc_plugins/zwick_blb/plugin.py
  - src/dpost/pc_plugins/haake_blb/plugin.py
  - src/dpost/pc_plugins/tischrem_blb/plugin.py
lane: Plugin-PC
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- PC plugin adapter for PC-side integration behavior.

## Origin Gist
- Source mapping: template derived from 8 PC-plugin origin files.
- Legacy gist: Keeps PC plugin module plugin.py for kinexus_blb. Keeps PC plugin module plugin.py for eirich_blb. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: PC plugin adapter for PC-side integration behavior.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Plugin host lifecycle calls (`initialize`, `activate_profile`, `shutdown`).
- Typed PC plugin settings.
- Sync/runtime context and profile selection metadata.
- Contract version metadata from `plugins/contracts`.

## Outputs
- Required PC plugin entry points:
  - `metadata()` returning plugin id/version/family metadata.
  - `capabilities()` returning explicit sync/upload capability flags.
  - `create_sync_adapter(settings)` returning sync-facing contract implementation.
  - `prepare_sync_payload(record, context)` returning normalized outbound payload.
- Optional lifecycle hooks (`before_sync`, `after_sync`, `on_shutdown`) with typed outcomes.
- Typed PC plugin errors for metadata/settings/sync adapter issues.

## Invariants
- `metadata().family` is `pc` and `plugin_id` remains stable.
- Capability flags are explicit booleans and drive host selection decisions.
- Required entry points are exported by every PC plugin implementation.
- Payload preparation is deterministic for identical record/context input.

## Failure Modes
- Missing required entry point export raises `PcPluginEntrypointError`.
- Metadata or capability shape violation raises `PcPluginMetadataError`.
- Sync adapter factory failure raises `PcPluginSyncAdapterError`.
- Payload preparation validation failure raises `PcPluginPayloadError`.

## Pseudocode
1. Implement required exports (`metadata`, `capabilities`, `create_sync_adapter`, `prepare_sync_payload`).
2. Return stable plugin metadata with family=`pc`, version, and supported profile tags.
3. Validate incoming settings/context and construct sync adapter instance.
4. Implement payload preparation for record sync operations.
5. Expose optional lifecycle hooks for sync orchestration integration.
6. Return typed errors for invalid metadata, settings, adapter, or payload conditions.

## Tests To Implement
- unit: required export presence, capability flags, sync adapter factory behavior, and payload preparation validation.
- integration: plugin host activates a concrete PC plugin from template and post-persist sync flow invokes its adapter/payload hooks successfully.



