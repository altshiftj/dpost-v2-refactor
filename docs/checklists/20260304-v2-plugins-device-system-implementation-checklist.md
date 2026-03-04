# Checklist: V2 Plugins Device-System Implementation

## Date
- 2026-03-04

## Objective
- Complete the `plugins-device-system` lane with TDD-first implementation of V2 plugin host/discovery/device integration under `src/dpost_v2/plugins/**` and `tests/dpost_v2/plugins/**`.

## Reference Set (Required)
- `docs/ops/lane-prompts/plugins-device-system.md`
- `docs/pseudocode/plugins/contracts.md`
- `docs/pseudocode/plugins/discovery.md`
- `docs/pseudocode/plugins/catalog.md`
- `docs/pseudocode/plugins/profile_selection.md`
- `docs/pseudocode/plugins/host.md`
- `docs/pseudocode/plugins/devices/_device_template/plugin.md`
- `docs/pseudocode/plugins/devices/_device_template/settings.md`
- `docs/pseudocode/plugins/devices/_device_template/processor.md`
- `docs/pseudocode/plugins/pcs/_pc_template/plugin.md`
- `docs/pseudocode/plugins/pcs/_pc_template/settings.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: TDD Red Phase
- Why this matters: codifying expected discovery/selection/loading behavior first prevents host runtime drift and keeps plugin boundaries explicit.

### Checklist
- [x] Added failing tests for discovery ordering, guarded import behavior, manifest validation, duplicate id handling, and allowed-family policy.
- [x] Added failing tests for profile selection determinism, unknown profile handling, override conflict handling, catalog mismatch handling, and precedence behavior.
- [x] Added failing tests for host contract gating, duplicate registration rejection, deterministic capability lookup, lifecycle activation/shutdown, and device processor creation.
- [x] Added integration tests for discovery -> activation -> device processor execution path.
- [x] Added tests for namespace-based discovery and concrete V2 plugin packages (`test_device`, `test_pc`).
- [x] Added tests for device/pc template settings and plugin entrypoint contracts.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins` fails before implementation with missing module/import errors (expected red state).

### Completion Notes
- How it was done: created plugin-lane tests first in `tests/dpost_v2/plugins/` and confirmed red collection/runtime failures before implementing runtime modules.

---

## Section: Core Plugin Runtime
- Why this matters: host/discovery/catalog/profile-selection are the core orchestration boundary for all device and PC plugin behavior.

### Checklist
- [x] Implemented plugin package exports in `src/dpost_v2/plugins/__init__.py`.
- [x] Implemented plugin-facing contracts aliases and compatibility helpers in `src/dpost_v2/plugins/contracts.py`.
- [x] Implemented deterministic discovery with diagnostics and fingerprinting in `src/dpost_v2/plugins/discovery.py`.
- [x] Implemented immutable catalog snapshot, query helpers, and refresh diff in `src/dpost_v2/plugins/catalog.py`.
- [x] Implemented deterministic profile selection policy with typed errors in `src/dpost_v2/plugins/profile_selection.py`.
- [x] Implemented plugin host registry/lifecycle/capability lookups and processor creation in `src/dpost_v2/plugins/host.py`.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins` passes host/discovery/selection/catalog tests.
- [x] `python -m ruff check src/dpost_v2/plugins tests/dpost_v2/plugins` passes for plugin lane files.

### Completion Notes
- How it was done: implemented minimal passing behavior per test slice, then refactored for deterministic ordering, typed error boundaries, and immutable snapshots.

---

## Section: Device and PC Integration
- Why this matters: lane completion requires real plugin package integration, not only synthetic test modules.

### Checklist
- [x] Added namespace package roots for device and PC plugins.
- [x] Implemented namespace discovery (`discover_from_namespaces`) with deterministic package enumeration and template package skipping by default.
- [x] Implemented device template package modules: `_device_template/plugin.py`, `_device_template/settings.py`, `_device_template/processor.py`.
- [x] Implemented PC template package modules: `_pc_template/plugin.py`, `_pc_template/settings.py`.
- [x] Implemented concrete V2 test device plugin package: `devices/test_device/{plugin,settings,processor}.py`.
- [x] Implemented concrete V2 test PC plugin package: `pcs/test_pc/{plugin,settings}.py`.
- [x] Verified integration test path activates discovered V2 `test_device` plugin and executes processor output deterministically.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins` includes namespace-discovery and concrete-plugin integration tests.

### Completion Notes
- How it was done: added concrete test plugins under V2 plugin namespaces, then used namespace discovery + host activation tests to validate end-to-end device integration.

---

## Section: Validation and Checkpoint
- Why this matters: lane completion needs explicit, reproducible quality evidence and a checkpoint commit.

### Checklist
- [x] Ran plugin-lane tests to completion.
- [x] Ran plugin-lane lint checks.
- [x] Confirmed clean working tree after checkpoint commit.
- [x] Created lane checkpoint commit: `149b8df` with scoped message `v2: plugins device-system host discovery templates`.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins` -> `30 passed`.
- [x] `python -m ruff check src/dpost_v2/plugins tests/dpost_v2/plugins` -> `All checks passed`.
- [x] `git status --short` -> clean.

### Completion Notes
- How it was done: executed lane-targeted tests/lint after each TDD slice, then committed final lane scope in one checkpoint commit.

---

## Section: Residual Risk Notes
- Why this matters: documenting remaining non-lane gaps prevents accidental over-claiming of global V2 completion.

### Checklist
- [x] Noted that this lane implements concrete V2 `test_device` and `test_pc` plugins only; full plugin family migration remains separate work.
- [x] Noted that full `tests/dpost_v2` run currently has an unrelated pre-existing collection-name collision outside plugin lane scope.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2` still reports unrelated `test_context.py` import mismatch in non-plugin directories.

### Completion Notes
- How it was done: kept lane edits scoped to plugin source/tests while recording cross-suite residual issues as out-of-scope observations.
