# Checklist: V2 Plugins Device-System Phase 2 Work Summary

## Date
- 2026-03-04

## Objective
- Record the completed Phase 2 lane work for `plugins-device-system` (mapped migration gap closure plus host/discovery hardening in TDD order).

## Scope
- Worktree: `D:\Repos\d-post\.worktrees\plugins-device-system`
- Implementation paths:
  - `src/dpost_v2/plugins/**`
  - `tests/dpost_v2/plugins/**`
- Summary/checkpoint references:
  - `docs/checklists/20260304-v2-plugins-device-system-phase2-hardening-checklist.md`
  - commits: `f4955f3`, `5c4f2ca`

---

## Section: Mapped Plugin Migration Gap Closure
- Why this matters: Phase 2 required concrete V1->V2 mapped device/pc plugin coverage before any extra scaffolding.

### Checklist
- [x] Confirmed mapped device plugin packages are discoverable in V2 namespace discovery (`dsv_horiba`, `erm_hioki`, `extr_haake`, `psa_horiba`, `rhe_kinexus`, `rmx_eirich_el1`, `rmx_eirich_r01`, `sem_phenomxl2`, `test_device`, `utm_zwick`).
- [x] Confirmed mapped PC plugin packages are discoverable in V2 namespace discovery (`eirich_blb`, `haake_blb`, `hioki_blb`, `horiba_blb`, `kinexus_blb`, `test_pc`, `tischrem_blb`, `zwick_blb`).
- [x] Kept plugin package boundaries explicit (`plugin.py`, `settings.py`, and `processor.py` for device plugins).

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_migration_coverage.py`

### Completion Notes
- Existing Phase 2 mapped migration work remained green and was preserved while hardening additional host/discovery behavior.

---

## Section: Discovery Hardening (Namespace Policy)
- Why this matters: Namespace policy must be deterministic and robust to configuration token formatting to prevent false family mismatches.

### Checklist
- [x] Added failing test: `test_namespace_discovery_normalizes_namespace_family_tokens`.
- [x] Normalized `namespace_families` family tokens in discovery (`strip().lower()`).
- [x] Added validation for malformed namespace mapping keys/family values and unsupported family tokens.
- [x] Ensured normalized family values are used consistently for both discovery allowed-family policy and namespace-family enforcement.

### Manual Check
- [x] Red phase: `python -m pytest -q tests/dpost_v2/plugins/test_namespace_discovery.py tests/dpost_v2/plugins/test_host.py` -> `2 failed, 7 passed`.
- [x] Green phase: `python -m pytest -q tests/dpost_v2/plugins/test_namespace_discovery.py tests/dpost_v2/plugins/test_host.py` -> `9 passed`.

### Completion Notes
- Runtime implementation change: `src/dpost_v2/plugins/discovery.py` now validates and normalizes namespace-family mapping before module enumeration and family checks.

---

## Section: Host Lifecycle Hardening (Profile Reactivation)
- Why this matters: Host lifecycle transitions must handle profile switches without duplicate activation hooks and must shutdown removed plugins predictably.

### Checklist
- [x] Added failing test: `test_host_profile_reactivation_handles_removed_and_unchanged_plugins`.
- [x] Updated activation flow to compute deltas between current active set and next selected set.
- [x] Added shutdown handling for removed plugins during profile change.
- [x] Limited activation hooks to newly added plugins only (unchanged plugins are not re-activated).
- [x] Preserved deterministic ordering for shutdown and activation transitions.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_host.py`

### Completion Notes
- Runtime implementation change: `src/dpost_v2/plugins/host.py` now applies lifecycle transitions by diff (`removed` then `added`) during `activate_profile`.

---

## Section: Lane Validation and Checkpoint Evidence
- Why this matters: Phase completion requires reproducible lane-scoped lint/test evidence and traceable commits.

### Checklist
- [x] Ran lane plugin lint gate.
- [x] Ran full lane plugin test suite after hardening.
- [x] Recorded scoped checkpoint commit for this hardening slice.
- [x] Confirmed clean worktree state after checkpoint.

### Manual Check
- [x] `python -m ruff check src/dpost_v2/plugins tests/dpost_v2/plugins` -> `All checks passed`.
- [x] `python -m pytest -q tests/dpost_v2/plugins` -> `36 passed`.
- [x] `git log --oneline -n 3` includes:
  - [x] `5c4f2ca v2: plugins harden namespace and lifecycle transitions`
  - [x] `f4955f3 v2: plugins close mapped migration gaps`
- [x] `git status --short` -> clean.

### Completion Notes
- Hardening work was delivered in TDD order: failing tests first, minimal runtime implementation, then lane-wide verification.

---

## Section: Risks and Assumptions
- Why this matters: Residual risk notes prevent overstating migration parity and document known boundaries of this lane slice.

### Checklist
- [x] Assumed namespace-family policy should treat family tokens case-insensitively and ignore surrounding whitespace.
- [x] Assumed profile reactivation should emit shutdown hooks for removed plugins and activation hooks only for newly added plugins.
- [x] Noted that concrete mapped plugin packages remain template-backed contract implementations, not full legacy processor parity ports.
- [x] Noted that activation rollback semantics are still partial if a later activation hook fails mid-transition.

### Manual Check
- [x] Contract and lane integration tests for discovery, selection, loading, and host lifecycle remain green in lane scope.

### Completion Notes
- No edits were made outside lane-relevant plugin runtime/tests for implementation behavior; this document is a reporting artifact for the completed lane work.
