# Checklist: V2 Pseudocode Traceability Refresh

## Objective
- Keep pseudocode-to-implementation and pseudocode-to-tests mapping current after each V2 lane lands.

## Section: Regenerate Matrix
- Why this matters: stale mapping causes silent drift between pseudocode and merged code.

### Checklist
- [ ] Recompute matrix rows for all non-README pseudocode specs with frontmatter `id`.
- [ ] Recompute implementation status by checking existence of `src/dpost_v2/<id>`.
- [ ] Recompute test traceability status by scanning direct imports in `tests/dpost_v2/**/test_*.py`.
- [ ] Overwrite `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`.

### Manual Check
- [ ] Matrix row count equals current pseudocode non-README spec count.
- [ ] Matrix has only these status values:
  - `implemented`
  - `missing_implementation`
  - `direct_module_tests_present`
  - `no_direct_module_test_import`
  - `missing_tests`

### Completion Notes
- How it was done: <fill after refresh>

---

## Section: Reconcile Gap Register
- Why this matters: unresolved gaps must stay explicit so implementation lanes can close them deterministically.

### Checklist
- [ ] Update the gap register in `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`.
- [ ] Keep ordering stable:
  - missing implementation and tests
  - implemented with no direct module test import
- [ ] Update coverage snapshot counts and area breakdown counts in the same report.

### Manual Check
- [ ] Every gap listed in the report is represented by at least one matrix row.
- [ ] No matrix gap row is omitted from the report.

### Completion Notes
- How it was done: <fill after refresh>

---

## Section: Publish Baseline Updates
- Why this matters: baseline pointers in planning docs must reflect the newest snapshot.

### Checklist
- [ ] If counts changed, update snapshot counts in:
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
- [ ] Ensure baseline links remain present in:
  - `docs/pseudocode/README.md`
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- [ ] Record a checkpoint commit with a docs-scoped message.

### Completion Notes
- How it was done: <fill after refresh>
