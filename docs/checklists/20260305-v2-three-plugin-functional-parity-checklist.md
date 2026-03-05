# Checklist: V2 Three-Plugin Functional Parity

## Execution Order (Start Here)
- Why this matters: The runtime handshake is closed, so the next work should focus only on device behavior parity and deterministic plugin outcomes.

### Manual Check
- [x] Handshake closeout is accepted from `docs/reports/20260305-v2-handshake-closeout-report.md`.
- [x] Manual probe matrix is accepted for:
  - `horiba_blb -> psa_horiba`
  - `tischrem_blb -> sem_phenomxl2`
  - `zwick_blb -> utm_zwick`

### Checklist
- [x] Treat `docs/checklists/20260305-v2-architecture-handshake-first-checklist.md` as closed for this phase.
- [x] Use `docs/planning/20260305-v2-three-plugin-phased-migration-rpc.md` as historical planning input only.
- [x] Parallel execution pack is available if this phase is lane-split:
  - `docs/planning/20260305-v2-three-plugin-parallel-lanes-rpc.md`
  - `docs/checklists/20260305-v2-three-plugin-parallel-coordination-checklist.md`
  - `docs/ops/lane-prompts/three-plugin-5-launch-pack.md`
- [x] Start execution with:
  - `Section: Behavior spec lock (TDD)`
  - `Section: sem_phenomxl2 parity slice (TDD)`

### Completion Notes
- How it was done:
  - Execution order was followed as planned:
    1. `lane0-spec-lock`
    2. `laneA-sem-phenomxl2`
    3. `laneB-utm-zwick`
    4. `laneC-psa-horiba`
    5. `laneD-closeout`

---

## Section: Baseline lock
- Why this matters: Functional parity work needs a stable V2 runtime baseline so plugin bugs are not confused with wiring regressions.

### Manual Check
- [x] `git status --short --branch` is captured in notes.
- [x] Handshake closeout report is referenced as the baseline runtime proof.

### Checklist
- [x] Re-use `docs/reports/20260305-v2-handshake-closeout-report.md` as the baseline lock.
- [x] Record current branch state and any local-only manual artifacts that must remain untracked.
- [x] Avoid re-running architecture bring-up unless runtime assumptions change.

### Completion Notes
- How it was done:
  - Baseline runtime proof remained:
    - `docs/reports/20260305-v2-handshake-closeout-report.md`
  - Closeout branch state was captured on `three-plugin/laneD-closeout` starting from `835e1e1` before lane intake.
  - Lane work remained isolated to worktrees; untracked lane log artifacts stayed outside the commit scope.

---

## Section: Behavior spec lock (TDD)
- Why this matters: The three plugin migrations need explicit parity targets before implementation starts, otherwise "done" will drift.

### Manual Check
- [x] Legacy source reference is identified for each target plugin.
- [x] Accepted/deferred behavior list exists for each target plugin.

### Checklist
- [x] Add red parity-spec tests for `sem_phenomxl2` under `tests/dpost_v2/plugins/devices/sem_phenomxl2/`.
- [x] Add red parity-spec tests for `utm_zwick` under `tests/dpost_v2/plugins/devices/utm_zwick/`.
- [x] Add red parity-spec tests for `psa_horiba` under `tests/dpost_v2/plugins/devices/psa_horiba/`.
- [x] Build a parity matrix mapping legacy behaviors to V2 test ids.
- [x] Record explicit accepted/deferred behaviors in completion notes.

### Completion Notes
- How it was done:
  - Legacy plugin source under `src/ipat_watchdog/device_plugins/**` was used as the primary reference.
  - Legacy reference tests under `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/**` were used as secondary evidence.
  - Published parity matrix:
    - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
  - Published findings/risk notes:
    - `docs/reports/20260305-v2-lane0-spec-lock-report.md`
  - Added red parity-spec tests under `tests/dpost_v2/plugins/devices/**`.

---

## Section: sem_phenomxl2 parity slice (TDD)
- Why this matters: SEM is the cleanest first migration target and establishes the pattern for moving real plugin behavior into V2 contracts.

### Manual Check
- [x] Headless runtime processes SEM sample artifacts under `tischrem_blb`.
- [x] Expected SEM-specific output behavior is visible in persisted payloads and filesystem side effects.

### Checklist
- [x] Add red tests for trailing-digit normalization behavior.
- [x] Add red tests for native image handling behavior.
- [x] Add red tests for ELID zip/descriptor flow behavior.
- [x] Implement minimal processor changes in `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py`.
- [x] Add or update runtime smoke for SEM parity path.

### Completion Notes
- How it was done:
  - Lane A delivered the SEM processor/settings slice and published:
    - `docs/reports/20260305-v2-laneA-sem-phenomxl2-report.md`
  - Closeout runtime probe under `tischrem_blb` succeeded end-to-end:
    - file moved to `processed/`
    - persisted `plugin_id="sem_phenomxl2"`
    - persisted `datatype="img"`

---

## Section: utm_zwick parity slice (TDD)
- Why this matters: Zwick introduces staged multi-file behavior and validates that V2 can hold series state without reintroducing legacy runtime patterns.

### Manual Check
- [ ] Headless runtime processes staged Zwick inputs under `zwick_blb`.
- [ ] Series state and final output behavior are deterministic across repeated runs.

### Checklist
- [x] Add red tests for `.zs2` plus sentinel `.xlsx` series assembly.
- [ ] Add red tests for TTL/flush behavior.
- [ ] Add red tests for unique move semantics and overwrite protection.
- [x] Implement minimal processor/state changes in `src/dpost_v2/plugins/devices/utm_zwick/processor.py`.
- [x] Add or update integration/runtime smoke for repeated series handling.

### Completion Notes
- How it was done:
  - Lane B delivered the Zwick processor/test slice and published:
    - `docs/reports/20260305-v2-laneB-utm-zwick-report.md`
  - Plugin-local parity is green, including staged `.zs2` gating and matching `.xlsx` finalization.
  - Shared runtime seam is now green:
    - raw `.zs2` defers without failing the watch loop
    - matching `.xlsx` finalizes and persists one record under `zwick_blb`
    - normalized processed payload paths are stored in sqlite
  - Deferred items remain:
    - TTL/session-end flush
    - unique move semantics/overwrite protection

---

## Section: psa_horiba parity slice (TDD)
- Why this matters: PSA adds bucketed/staged pairing logic and is the best final target once the simpler and staged-series paths are already proven in V2.

### Manual Check
- [ ] Headless runtime processes PSA sample artifacts under `horiba_blb`.
- [ ] Bucket/pair/flush behavior is deterministic and leaves expected final artifacts.

### Checklist
- [x] Add red tests for bucketed pairing behavior.
- [x] Add red tests for staged flush and sequence naming.
- [x] Add red tests for zip behavior and stale purge behavior.
- [x] Implement minimal processor/state changes in `src/dpost_v2/plugins/devices/psa_horiba/processor.py`.
- [x] Add or update integration/runtime smoke for PSA staged handling.

### Completion Notes
- How it was done:
  - Lane C delivered the PSA plugin/processor/settings/test slice and published:
    - `docs/reports/20260305-v2-laneC-psa-horiba-report.md`
  - Plugin-local parity is green for:
    - `.tsv` acceptance
    - bucketed pairing
    - deterministic staged-folder naming
    - numbered `.csv` and `.zip` outputs
    - conservative stale-state purge
  - Shared runtime seam is now green:
    - raw staged events defer without failing the watch loop
    - a full bucket/sentinel batch finalizes and persists one record under `horiba_blb`
    - numbered `.csv` and `.zip` outputs land in `processed/`
  - Deferred items remain:
    - rename-cancel whole-folder handling
    - exception-bucket handling

---

## Section: Cross-plugin closeout
- Why this matters: Before declaring the migration phase complete, the three plugins must be proven together under the real standalone headless path.

### Manual Check
- [ ] Manual matrix passes for all three workstation/device pairs on current branch.
- [ ] Persisted sqlite payloads reflect plugin-specific behavior, not only generic routing/persist fields.
- [ ] No fallback processor/runtime path is exercised during the final probes.

### Checklist
- [x] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [x] Run targeted plugin/runtime/integration suites for the three migrated plugins.
- [x] Run `python -m pytest -q tests/dpost_v2`.
- [x] Publish a migration closeout report in `docs/reports/` with residual risks and deferred parity gaps.

### Completion Notes
- How it was done:
  - Ran `python -m ruff check src/dpost_v2 tests/dpost_v2` and it passed.
  - Ran targeted checks:
    - `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/runtime/test_composition.py`
    - `python -m pytest -q tests/dpost_v2/plugins/test_migration_coverage.py`
  - Ran full suite:
    - `python -m pytest -q tests/dpost_v2`
    - result: `426 passed`
  - Published:
    - `docs/reports/20260305-v2-staged-runtime-seam-report.md`
    - `docs/reports/20260305-v2-three-plugin-closeout-report.md`
  - Closeout is green for the accepted three-plugin parity scope; remaining deferred items are explicitly documented and out of scope for this phase.
