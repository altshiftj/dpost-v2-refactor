---
id: plugins/catalog.py
origin_v1_files:
  - src/dpost/plugins/reference.py
lane: Plugin-Host
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Plugin metadata catalog and lookup APIs.

## Origin Gist
- Source mapping: `src/dpost/plugins/reference.py`.
- Legacy gist: Renames reference to catalog metadata module.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Plugin metadata catalog and lookup APIs.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Valid plugin descriptors from discovery/host registration.
- Catalog query requests (by id, by family, by capability, by profile).
- Optional catalog refresh snapshots.
- Version/fingerprint metadata for registry updates.

## Outputs
- Immutable catalog snapshot with indexed lookup structures.
- Query API responses returning plugin metadata views.
- Catalog diff output for refresh operations.
- Typed catalog errors for unknown ids or invalid query filters.

## Invariants
- Catalog snapshot is immutable once published.
- Query results are deterministic for same snapshot and filters.
- Indexes stay synchronized with source descriptor set.
- Catalog version increments on every descriptor-set change.

## Failure Modes
- Unknown plugin id query raises `PluginCatalogNotFoundError`.
- Invalid filter combination raises `PluginCatalogQueryError`.
- Snapshot build with duplicate ids raises `PluginCatalogDuplicateError`.
- Refresh with stale version token raises `PluginCatalogVersionError`.

## Pseudocode
1. Build catalog snapshot from validated descriptors and compute version fingerprint.
2. Construct indexes by id, plugin family, capabilities, and profile tags.
3. Implement query functions that read from immutable indexes only.
4. Implement `refresh(new_descriptors)` returning diff + new snapshot/version.
5. Validate query/filter inputs and return typed catalog errors for invalid lookups.
6. Expose lightweight metadata views for host, processor factory, and profile selection policy.

## Tests To Implement
- unit: index construction, deterministic query ordering, snapshot immutability, and refresh diff behavior.
- integration: discovery/host/profile-selection consume one catalog snapshot and resolve consistent plugin metadata across runtime flow.



