# Checklist Template

## Section: Requirements confirmation
- Why this matters: avoids mismatched prefix rules and data loss.

### Checklist
- [x] Confirm sentinel `.xlsx` naming relative to `.zs2` prefix.
- [x] Confirm whether incomplete `.zs2` series should flush on session end.
- [x] Confirm expected primary datatype (`xlsx` vs `zs2`).

### Completion Notes
- How it was done: Confirmed exact prefix match, 30-minute TTL flush, and `xlsx` as primary datatype.

---

## Section: Preprocessing updates
- Why this matters: ensures the pipeline only triggers on the correct sentinel.

### Checklist
- [ ] Update preprocessing to stage `.zs2` and wait for sentinel `.xlsx`.
- [ ] Implement prefix validation for `usr-inst-sample_name`.
- [ ] Ignore or reject `.txt`/`.csv` artifacts.

### Completion Notes
- How it was done: TBD

---

## Section: Processing updates
- Why this matters: guarantees correct record contents and naming.

### Checklist
- [ ] Move `.zs2` into record with unique naming.
- [ ] Move sentinel `.xlsx` into record with unique naming.
- [ ] Update `ProcessingOutput.datatype` to agreed type.

### Completion Notes
- How it was done: TBD

---

## Section: Config + probe updates
- Why this matters: reduces false matches and avoids misrouting files.

### Checklist
- [ ] Update `probe_file` to match only `.zs2` and `.xlsx`.
- [ ] Restrict `exported_extensions` to `.xlsx` if appropriate.

### Completion Notes
- How it was done: TBD

---

## Section: Tests
- Why this matters: protects against regressions.

### Checklist
- [ ] Write failing unit tests for sentinel workflow (TDD step).
- [ ] Update integration tests to new workflow assumptions.
- [ ] Run `python -m pytest` after implementation.

### Completion Notes
- How it was done: TBD

---

## Section: Documentation and glossary
- Why this matters: keeps team aligned on terminology.

### Checklist
- [ ] Add glossary entries for new terms.
- [ ] Update any device documentation if needed.

### Completion Notes
- How it was done: TBD
