# RPC: NamingSettings as Single Source of Truth

## Date
- 2026-02-24

## Status
- Draft

## Context
- Naming behavior is currently split between explicit context passing and ambient lookups via `current()` wrappers.
- `NamingSettings` already exists in `src/dpost/application/config/schema.py`, but naming behavior is still diffuse across wrappers and fallback/inference paths.
- Team direction: make naming rules explicit, centralized, and constructor-driven.

## Working Tracker Set
- Baseline findings report:
  - `docs/reports/20260302-naming-settings-sot-migration-baseline-report.md`
- Execution checklist:
  - `docs/checklists/20260302-naming-settings-sot-migration-execution-checklist.md`

## Why Current Policy Architecture Exists (How It Got Here)
- The current `application/naming/policy.py` facade and related seams were introduced as an intentional migration bridge, not as final architecture.
- Evolution summary:
  1. Legacy baseline had naming/separator behavior tied to constants and scattered call sites (records, sync, plugins), creating hidden coupling.
  2. Phase 4 migration moved naming reads toward config-authoritative behavior and removed many legacy constant reads while preserving runtime behavior.
  3. Part 3 domain extraction moved pure naming rules into domain modules (`domain.naming.prefix_policy`, `domain.naming.identifiers`) to enforce clean layering.
  4. Application naming facade was kept to apply active runtime config to domain-pure functions while callers were incrementally rewired.
  5. Later refactors pushed explicit context deeper (separator/pattern forwarding), but deliberately deferred some compatibility wrappers to avoid risky one-shot churn.
- In short: today's policy architecture is a staged strangler outcome prioritizing behavior stability first, then explicit-context purity.

### Historical Evidence
- Legacy/runtime config read inventory and separator migration context:
  - `docs/reports/archive/20260218-phase4-runtime-config-read-inventory.md`
- Phase/checklist evidence of naming/constants consolidation and fail-fast moves:
  - `docs/checklists/archive/20260218-dpost-architecture-tightening-checklist.md`
  - `docs/planning/archive/20260218-dpost-execution-board.md`
- Domain naming ownership extraction rationale:
  - `docs/reports/archive/20260221-part3-domain-layer-extraction-inventory.md`
- Coverage/refactor slice documenting Kadi separator seam extraction:
  - `docs/reports/archive/20260221-coverage-informed-architecture-findings.md`
- Deferred-wrapper note explaining why some ambient seams remain temporarily:
  - `docs/reports/archive/20260222-current-snapshot-improvement-opportunities.md`

## Decision
- Keep `NamingSettings` in `src/dpost/application/config/schema.py`.
- Treat `NamingSettings` as the canonical naming contract for runtime behavior.
- Expand `NamingSettings` into an explicit constructor-like config object that owns:
  - structural parts (`user`, `institute`, `sample_name`),
  - `id_separator`,
  - filename pattern construction.
- Runtime and application consumers should receive naming context explicitly and stop relying on ambient `current()` lookups in non-composition paths.

## Proposed `NamingSettings` Shape
- Keep in schema layer (application config contract), not a separate module.
- Explicit fields (example intent):
  - `id_separator: str = "-"`
  - `part_order: tuple[str, str, str] = ("user", "institute", "sample_name")`
  - `sample_max_len: int = 30`
  - `allow_sample_spaces: bool = True`
  - `filename_pattern: Pattern[str]` derived/validated in `__post_init__`.
- Canonical prefix format target:
  - `user{id_separator}institute{id_separator}sample_name`

## Why Keep It in `schema.py`
- `NamingSettings` is configuration policy, so schema is the correct ownership boundary.
- Keeping it in schema avoids introducing duplicate naming contracts in other layers.
- It reinforces a single source of truth for naming across runtime, processing, records, storage, and sync.

## Migration Direction
1. Thread explicit naming context from config/orchestrators to all naming consumers.
2. Keep `application/naming/policy.py` only as a temporary seam during migration.
3. Remove ambient `current().id_separator` / `current().filename_pattern` reads from non-composition paths.
4. Remove local separator inference/fallback logic in `LocalRecord` and `KadiSyncManager` after explicit context is fully adopted.
5. Retire or minimize `application/naming/policy.py` once direct explicit usage is complete.

## Acceptance Criteria
- `NamingSettings` in schema is the single authoritative owner of naming structure + pattern.
- No production naming behavior depends on ambient `current()` lookup outside designated boundary seams.
- No separator inference/fallback in domain/infrastructure naming consumers.
- Naming-related tests pass with explicit-context behavior.

## Deferred Follow-up: Runtime Naming Overload Cleanup (Documented for Later)
- Goal: reduce naming ambiguity where "runtime" currently refers to different concerns across layers.
- Clarification of current intent:
  - `src/dpost/runtime/` owns startup/composition policy.
  - `src/dpost/application/config/runtime.py` owns active config context helpers.
  - `src/dpost/infrastructure/runtime/` owns concrete runtime adapters.
- Recommended low-risk rename path (deferred):
  1. Rename `src/dpost/application/config/runtime.py` to
     `src/dpost/application/config/context.py`.
  2. Rename `src/dpost/infrastructure/runtime/bootstrap_dependencies.py` to
     `src/dpost/infrastructure/runtime/startup_dependencies.py`.
  3. Optional final step (higher churn): rename folder
     `src/dpost/infrastructure/runtime/` to
     `src/dpost/infrastructure/runtime_adapters/`.
- Rationale:
  - improves contributor readability without changing architecture boundaries.
  - keeps dependency direction unchanged while reducing overloaded terminology.
  - supports gradual migration with minimal blast radius.

## Notes
- This direction is compatible with current architecture layering:
  - domain remains pure,
  - application orchestrates context,
  - infrastructure consumes explicit inputs,
  - runtime/composition wires dependencies.
