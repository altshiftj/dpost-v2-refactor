# Checklist: Lane D Closeout

## Section: Integration intake
- Why this matters: Closeout should start from merged plugin-lane results, not speculative expectations.

### Checklist
- [ ] Confirm `laneA`, `laneB`, and `laneC` are merged.
- [ ] Review plugin-lane deferred-risk notes.
- [ ] Confirm shared runtime surfaces did not regress during lane merges.

### Completion Notes
- How it was done:

---

## Section: Cross-plugin runtime proof
- Why this matters: The migration phase is only done when the three plugins work together on the real standalone headless path.

### Checklist
- [ ] Re-run runtime smoke for `horiba_blb -> psa_horiba`.
- [ ] Re-run runtime smoke for `tischrem_blb -> sem_phenomxl2`.
- [ ] Re-run runtime smoke for `zwick_blb -> utm_zwick`.
- [ ] Confirm persisted sqlite payloads reflect plugin-specific behavior.

### Completion Notes
- How it was done:

---

## Section: Final gates and report
- Why this matters: The three-plugin phase needs one final measurable quality gate and a written handoff artifact.

### Checklist
- [ ] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [ ] Run targeted plugin and runtime suites.
- [ ] Run `python -m pytest -q tests/dpost_v2`.
- [ ] Publish the migration closeout report.

### Completion Notes
- How it was done:
