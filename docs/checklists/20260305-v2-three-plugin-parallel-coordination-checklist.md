# Checklist: V2 Three-Plugin Parallel Coordination

## Section: Lane bootstrap
- Why this matters: Parallel execution fails quickly when ownership and sequencing are vague.

### Checklist
- [x] Confirm the handshake closeout report is the accepted runtime baseline.
- [x] Create one branch/worktree per lane before implementation starts.
- [x] Assign one exact allowed edit scope per lane with no overlap.
- [x] Confirm `lane0-spec-lock` starts before plugin implementation lanes.

### Completion Notes
- How it was done:
  - Accepted runtime baseline:
    - `docs/reports/20260305-v2-handshake-closeout-report.md`
  - Created lane branches from `main` at commit `367edc2`:
    - `three-plugin/lane0-spec-lock`
    - `three-plugin/laneA-sem-phenomxl2`
    - `three-plugin/laneB-utm-zwick`
    - `three-plugin/laneC-psa-horiba`
    - `three-plugin/laneD-closeout`
  - Created local worktrees:
    - `.worktrees/lane0-spec-lock`
    - `.worktrees/laneA-sem-phenomxl2`
    - `.worktrees/laneB-utm-zwick`
    - `.worktrees/laneC-psa-horiba`
    - `.worktrees/laneD-closeout`
  - Launch order for the wave:
    1. `lane0-spec-lock`
    2. `laneA-sem-phenomxl2`
    3. `laneB-utm-zwick`
    4. `laneC-psa-horiba`
    5. `laneD-closeout`

---

## Section: Spec lock publication
- Why this matters: Plugin lanes need one stable parity target before they start implementing behavior.

### Checklist
- [x] Publish parity-spec tests for all three plugins.
- [x] Publish accepted/deferred behavior notes for all three plugins.
- [x] Confirm plugin lanes only consume the spec-lock output and do not redefine parity independently.

### Completion Notes
- How it was done:
  - Published red parity-spec tests for:
    - `sem_phenomxl2`
    - `utm_zwick`
    - `psa_horiba`
  - Published the visible handoff matrix:
    - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
  - Published the lane0 findings/risk report:
    - `docs/reports/20260305-v2-lane0-spec-lock-report.md`
  - Lane A/B/C should treat the matrix and test ids as the parity target instead of re-deriving behavior from the legacy repo independently.

---

## Section: Lane integration control
- Why this matters: Shared runtime and docs surfaces can become a merge bottleneck if plugin lanes drift into them.

### Checklist
- [x] Keep shared runtime and coordination docs centralized.
- [x] Integrate plugin lanes only after their targeted gates are green.
- [x] Re-run full V2 suite after integrated lane intake if shared helpers were touched.

### Completion Notes
- How it was done:
  - Runtime/composition and closeout docs were updated only in `laneD-closeout`.
  - Lane intake happened only after the lane-local gates were green:
    - `laneA-sem-phenomxl2` at `a4f289a`
    - `laneB-utm-zwick` at `cc4ce02`
    - `laneC-psa-horiba` at `3dd0457`
  - Re-ran:
    - `python -m ruff check src/dpost_v2 tests/dpost_v2`
    - targeted plugin/runtime suites
    - `python -m pytest -q tests/dpost_v2`
  - Intake initially revealed the staged-runtime blocker, which was then closed in:
    - `docs/reports/20260305-v2-staged-runtime-seam-report.md`

---

## Section: Final closeout
- Why this matters: The migration phase is not done until the three plugins are proven together on the real V2 path.

### Checklist
- [x] Execute `laneD-closeout` last.
- [x] Run full `ruff`, targeted plugin/runtime suites, and full `tests/dpost_v2`.
- [x] Publish the cross-plugin migration closeout report.

### Completion Notes
- How it was done:
  - `laneD-closeout` consumed the committed lane outputs after plugin lanes completed.
  - Published:
    - `docs/reports/20260305-v2-staged-runtime-seam-report.md`
    - `docs/reports/20260305-v2-three-plugin-closeout-report.md`
  - Final status:
    - plugin-local parity slices are committed and documented
    - shared staged/deferred runtime seam is green
    - cross-plugin closeout gates are green for the accepted phase scope
