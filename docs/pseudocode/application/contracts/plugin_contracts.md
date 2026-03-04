---
id: application/contracts/plugin_contracts.py
origin_v1_files:
  - src/dpost/application/processing/file_processor_abstract.py
  - src/dpost/plugins/contracts.py
lane: Contracts-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Plugin capability protocols, processor abstract types, plugin metadata types.

## Origin Gist
- Source mapping: `src/dpost/application/processing/file_processor_abstract.py`, `src/dpost/plugins/contracts.py`.
- Legacy gist: Moves processor abstraction into plugin contracts. Promotes plugin contract model to contract-first application boundary.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Plugin capability protocols, processor abstract types, plugin metadata types.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Plugin metadata discovered at startup (`plugin_id`, version, supported device/pc families).
- Processing requests containing candidate metadata and processing context.
- Optional plugin settings snapshots selected by runtime profile.
- Capability declarations reported by plugin modules.

## Outputs
- Protocol definitions for device plugin, PC plugin, and file processor contracts.
- Typed metadata models describing plugin identity, capabilities, and lifecycle hooks.
- Processor result model contract that ingestion stages consume without importing plugin internals.
- Validation helpers for capability declarations and processor outputs.

## Invariants
- `plugin_id` is globally unique within a runtime instance.
- A plugin that claims `can_process` must provide a processor factory with deterministic output type.
- Processor methods are side-effect free from contract perspective; side effects route through runtime services.
- Capability flags are explicit booleans; implicit defaults are forbidden.

## Failure Modes
- Missing required plugin entry points causes `PluginContractError` during discovery/registration.
- Duplicate plugin ids cause `DuplicatePluginRegistrationError`.
- Processor factory returning an object that violates protocol causes `InvalidProcessorError`.
- Capability validation mismatch causes plugin to be marked unavailable for the session.

## Pseudocode
1. Define protocol interfaces: `DevicePluginContract`, `PcPluginContract`, `ProcessorContract`.
2. Define metadata dataclasses: `PluginMetadata`, `PluginCapabilities`, `ProcessorDescriptor`.
3. Define `validate_plugin_contract(module_exports)` that checks required callables and metadata schema.
4. Define `validate_processor_result(result)` used by ingestion runtime to gate downstream stage execution.
5. Expose narrow helper aliases for plugins package so plugin authors depend on stable contract names only.
6. Specify compatibility rule: contract changes require version bump in plugin metadata.

## Tests To Implement
- unit: contract validator catches missing exports, duplicate ids, and invalid capability combinations.
- integration: plugin discovery + host + processor factory can register and execute both device and PC template plugins through the same contract surface.



