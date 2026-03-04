---
id: plugins/discovery.py
origin_v1_files:
  - src/dpost/plugins/loading.py
lane: Plugin-Host
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Plugin discovery/registration from modules/manifests.

## Origin Gist
- Source mapping: `src/dpost/plugins/loading.py`.
- Legacy gist: Renames loader to explicit discovery module.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Plugin discovery/registration from modules/manifests.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Plugin search roots and package namespace settings.
- Discovery policy (allowlist/denylist, device/pc plugin families, manifest requirement mode).
- Module loader/import helper with sandboxed error capture.
- Optional cache of prior discovery snapshots.

## Outputs
- Ordered list of discovered plugin descriptors.
- Discovery diagnostics (skipped modules, warnings, invalid manifests).
- Typed discovery errors for malformed plugins or loader failures.
- Snapshot fingerprint used for cache invalidation/reload checks.

## Invariants
- Discovery order is deterministic (stable sorted by plugin id/path).
- Discovery does not activate plugins; it only describes candidates.
- Descriptor schema is validated before output.
- Invalid plugin modules do not crash full discovery pass.

## Failure Modes
- Module import/load failure yields `PluginDiscoveryImportError`.
- Missing/invalid manifest metadata yields `PluginDiscoveryManifestError`.
- Duplicate plugin id in discovery set yields `PluginDiscoveryDuplicateIdError`.
- Unsupported plugin family token yields `PluginDiscoveryFamilyError`.

## Pseudocode
1. Resolve plugin search paths from settings and enumerate candidate modules.
2. Load module metadata/manifests with guarded import wrapper.
3. Validate descriptor schema and collect valid descriptors.
4. Detect duplicate plugin ids and conflicting metadata.
5. Sort descriptors deterministically and compute snapshot fingerprint.
6. Return descriptor list plus diagnostics/errors to host/catalog.

## Tests To Implement
- unit: deterministic ordering, manifest validation, duplicate-id detection, and guarded import error handling.
- integration: plugin host receives discovery descriptors from both device and pc plugin families and skips invalid modules without aborting valid discovery.



