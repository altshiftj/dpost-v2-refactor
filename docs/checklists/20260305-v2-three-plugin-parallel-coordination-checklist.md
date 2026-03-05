# Checklist: V2 Three-Plugin Parallel Coordination

## Section: Lane bootstrap
- Why this matters: Parallel execution fails quickly when ownership and sequencing are vague.

### Checklist
- [ ] Confirm the handshake closeout report is the accepted runtime baseline.
- [ ] Create one branch/worktree per lane before implementation starts.
- [ ] Assign one exact allowed edit scope per lane with no overlap.
- [ ] Confirm `lane0-spec-lock` starts before plugin implementation lanes.

### Completion Notes
- How it was done:

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
