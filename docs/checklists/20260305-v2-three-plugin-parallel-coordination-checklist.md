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
- [ ] Publish parity-spec tests for all three plugins.
- [ ] Publish accepted/deferred behavior notes for all three plugins.
- [ ] Confirm plugin lanes only consume the spec-lock output and do not redefine parity independently.

### Completion Notes
- How it was done:

---

## Section: Lane integration control
- Why this matters: Shared runtime and docs surfaces can become a merge bottleneck if plugin lanes drift into them.

### Checklist
- [ ] Keep shared runtime and coordination docs centralized.
- [ ] Merge plugin lanes only after their targeted gates are green.
- [ ] Re-run full V2 suite after each merged plugin lane if shared helpers were touched.

### Completion Notes
- How it was done:

---

## Section: Final closeout
- Why this matters: The migration phase is not done until the three plugins are proven together on the real V2 path.

### Checklist
- [ ] Merge `laneD-closeout` last.
- [ ] Run full `ruff`, targeted plugin/runtime suites, and full `tests/dpost_v2`.
- [ ] Publish the cross-plugin migration closeout report.

### Completion Notes
- How it was done:
