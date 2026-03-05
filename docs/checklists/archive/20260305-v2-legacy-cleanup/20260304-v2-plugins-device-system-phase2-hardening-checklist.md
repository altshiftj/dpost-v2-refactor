# Checklist: V2 Plugins Device-System Phase 2 Hardening and Gap Closure

## Date
- 2026-03-04

## Objective
- Complete Phase 2 for lane `plugins-device-system` by closing mapped V1->V2 concrete plugin package gaps and hardening namespace discovery/host integration with test-first execution.

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

## Section: TDD Red Phase for Gap Closure
- Why this matters: phase-2 hardening must be driven by failing tests for mapped migration completeness and discovery policy edge cases.

### Checklist
- [x] Added failing tests asserting full mapped namespace discovery coverage for device and PC plugin families.
- [x] Added failing tests asserting host activation and processor creation across the full mapped device set.
- [x] Added failing tests asserting mapped PC plugin sync adapter/payload contract behavior.
- [x] Added failing test asserting namespace family mismatch is rejected (`device` namespace cannot load `pc` metadata and vice versa).

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_namespace_discovery.py tests/dpost_v2/plugins/test_migration_coverage.py` failed in red phase (`4 failed, 2 passed`).

### Completion Notes
- How it was done: introduced new migration coverage tests and a namespace-family policy failure case before implementing additional concrete plugin packages and discovery checks.

---

## Section: Concrete Mapped Plugin Migration
- Why this matters: lane focus requires prioritizing mapped concrete V1->V2 plugin families over template-only scaffolding.

### Checklist
- [x] Added concrete device plugin packages for mapped families: `dsv_horiba`, `erm_hioki`, `extr_haake`, `psa_horiba`, `rhe_kinexus`, `rmx_eirich_el1`, `rmx_eirich_r01`, `sem_phenomxl2`, `utm_zwick`.
- [x] Added concrete PC plugin packages for mapped families: `eirich_blb`, `haake_blb`, `hioki_blb`, `horiba_blb`, `kinexus_blb`, `tischrem_blb`, `zwick_blb`.
- [x] Kept plugin boundaries explicit by implementing each package with local `plugin.py` + `settings.py` (+ `processor.py` for device plugins).
- [x] Preserved contract stability (`metadata`, `capabilities`, `validate_settings`, factories, lifecycle hooks).

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_migration_coverage.py` passed after implementation (`3 passed` within full run).

### Completion Notes
- How it was done: created concrete mapped plugin packages under `src/dpost_v2/plugins/devices/**` and `src/dpost_v2/plugins/pcs/**` using minimal template-backed runtime behavior to satisfy host/discovery contracts deterministically.

---

## Section: Discovery and Host Hardening
- Why this matters: discovery and host lifecycle behavior must be resilient to policy violations and expanded plugin sets.

### Checklist
- [x] Hardened `discover_from_namespaces` to enforce namespace-family policy against descriptor metadata family.
- [x] Verified that family mismatch raises `PluginDiscoveryFamilyError` with deterministic diagnostics.
- [x] Updated built-in integration test assertions to validate inclusion/exclusion semantics rather than singleton assumptions.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_namespace_discovery.py` passed with new family mismatch case.
- [x] `python -m pytest -q tests/dpost_v2/plugins/test_device_integration.py` passed after expectation update.

### Completion Notes
- How it was done: tracked expected family by discovered namespace module and raised typed error on mismatch; adjusted integration expectation to reflect mapped family expansion.

---

## Section: Validation and Checkpoint
- Why this matters: lane completion requires reproducible test/lint evidence plus a stable checkpoint commit.

### Checklist
- [x] Ran complete lane plugin test suite after implementation.
- [x] Ran lane plugin lint checks after implementation.
- [x] Confirmed clean working tree after checkpoint commit.
- [x] Created scoped checkpoint commit for this phase-2 slice.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/plugins` -> `34 passed`.
- [x] `python -m ruff check src/dpost_v2/plugins tests/dpost_v2/plugins` -> `All checks passed`.
- [x] `git status --short` -> clean.
- [x] Commit created: `f4955f3` (`v2: plugins close mapped migration gaps`).

### Completion Notes
- How it was done: executed TDD red/green cycles for the new migration-hardening slices, then re-ran lane-wide checks and committed all lane-scoped plugin changes.

---

## Section: Residual Risk Notes
- Why this matters: documenting remaining risk avoids overstating parity and informs next migration slices.

### Checklist
- [x] Noted that concrete mapped packages are currently template-backed for behavior and not full legacy processor parity ports.
- [x] Noted that PC sync endpoints in concrete packages are deterministic placeholders for contract/runtime testing.

### Manual Check
- [x] Contract and lane integration tests pass for discovery, selection, loading, and host lifecycle behavior in lane scope.

### Completion Notes
- How it was done: maintained strict lane scope (`src/dpost_v2/plugins/**`, `tests/dpost_v2/plugins/**`) and prioritized mapped package completeness plus host/discovery hardening per phase requirements.
