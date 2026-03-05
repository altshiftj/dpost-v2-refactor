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
- [ ] Start execution with:
  - `Section: Behavior spec lock (TDD)`
  - `Section: sem_phenomxl2 parity slice (TDD)`

### Completion Notes
- How it was done:

---

## Section: Baseline lock
- Why this matters: Functional parity work needs a stable V2 runtime baseline so plugin bugs are not confused with wiring regressions.

### Manual Check
- [ ] `git status --short --branch` is captured in notes.
- [ ] Handshake closeout report is referenced as the baseline runtime proof.

### Checklist
- [ ] Re-use `docs/reports/20260305-v2-handshake-closeout-report.md` as the baseline lock.
- [ ] Record current branch state and any local-only manual artifacts that must remain untracked.
- [ ] Avoid re-running architecture bring-up unless runtime assumptions change.

### Completion Notes
- How it was done:

---

## Section: Behavior spec lock (TDD)
- Why this matters: The three plugin migrations need explicit parity targets before implementation starts, otherwise "done" will drift.

### Manual Check
- [ ] Legacy source reference is identified for each target plugin.
- [ ] Accepted/deferred behavior list exists for each target plugin.

### Checklist
- [ ] Add red parity-spec tests for `sem_phenomxl2` under `tests/dpost_v2/plugins/devices/sem_phenomxl2/`.
- [ ] Add red parity-spec tests for `utm_zwick` under `tests/dpost_v2/plugins/devices/utm_zwick/`.
- [ ] Add red parity-spec tests for `psa_horiba` under `tests/dpost_v2/plugins/devices/psa_horiba/`.
- [ ] Build a parity matrix mapping legacy behaviors to V2 test ids.
- [ ] Record explicit accepted/deferred behaviors in completion notes.

### Completion Notes
- How it was done:

---

## Section: sem_phenomxl2 parity slice (TDD)
- Why this matters: SEM is the cleanest first migration target and establishes the pattern for moving real plugin behavior into V2 contracts.

### Manual Check
- [ ] Headless runtime processes SEM sample artifacts under `tischrem_blb`.
- [ ] Expected SEM-specific output behavior is visible in persisted payloads and filesystem side effects.

### Checklist
- [ ] Add red tests for trailing-digit normalization behavior.
- [ ] Add red tests for native image handling behavior.
- [ ] Add red tests for ELID zip/descriptor flow behavior.
- [ ] Implement minimal processor changes in `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py`.
- [ ] Add or update runtime smoke for SEM parity path.

### Completion Notes
- How it was done:

---

## Section: utm_zwick parity slice (TDD)
- Why this matters: Zwick introduces staged multi-file behavior and validates that V2 can hold series state without reintroducing legacy runtime patterns.

### Manual Check
- [ ] Headless runtime processes staged Zwick inputs under `zwick_blb`.
- [ ] Series state and final output behavior are deterministic across repeated runs.

### Checklist
- [ ] Add red tests for `.zs2` plus sentinel `.xlsx` series assembly.
- [ ] Add red tests for TTL/flush behavior.
- [ ] Add red tests for unique move semantics and overwrite protection.
- [ ] Implement minimal processor/state changes in `src/dpost_v2/plugins/devices/utm_zwick/processor.py`.
- [ ] Add or update integration/runtime smoke for repeated series handling.

### Completion Notes
- How it was done:

---

## Section: psa_horiba parity slice (TDD)
- Why this matters: PSA adds bucketed/staged pairing logic and is the best final target once the simpler and staged-series paths are already proven in V2.

### Manual Check
- [ ] Headless runtime processes PSA sample artifacts under `horiba_blb`.
- [ ] Bucket/pair/flush behavior is deterministic and leaves expected final artifacts.

### Checklist
- [ ] Add red tests for bucketed pairing behavior.
- [ ] Add red tests for staged flush and sequence naming.
- [ ] Add red tests for zip behavior and stale purge behavior.
- [ ] Implement minimal processor/state changes in `src/dpost_v2/plugins/devices/psa_horiba/processor.py`.
- [ ] Add or update integration/runtime smoke for PSA staged handling.

### Completion Notes
- How it was done:

---

## Section: Cross-plugin closeout
- Why this matters: Before declaring the migration phase complete, the three plugins must be proven together under the real standalone headless path.

### Manual Check
- [ ] Manual matrix passes for all three workstation/device pairs on current branch.
- [ ] Persisted sqlite payloads reflect plugin-specific behavior, not only generic routing/persist fields.
- [ ] No fallback processor/runtime path is exercised during the final probes.

### Checklist
- [ ] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [ ] Run targeted plugin/runtime/integration suites for the three migrated plugins.
- [ ] Run `python -m pytest -q tests/dpost_v2`.
- [ ] Publish a migration closeout report in `docs/reports/` with residual risks and deferred parity gaps.

### Completion Notes
- How it was done:
