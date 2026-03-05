# Checklist: Lane D Closeout

## Section: Integration intake
- Why this matters: Closeout should start from committed plugin-lane results, not speculative expectations.

### Checklist
- [x] Confirm `laneA`, `laneB`, and `laneC` are integrated for closeout.
- [x] Review plugin-lane deferred-risk notes.
- [ ] Confirm shared runtime surfaces did not regress during lane integration.

### Completion Notes
- How it was done:
  - Integrated committed lane payloads into `laneD-closeout` from:
    - `lane0-spec-lock` at `b33d33e`
    - `laneA-sem-phenomxl2` at `a4f289a`
    - `laneB-utm-zwick` at `cc4ce02`
    - `laneC-psa-horiba` at `3dd0457`
  - Reviewed deferred-risk notes from:
    - `docs/reports/20260305-v2-lane0-spec-lock-report.md`
    - `docs/reports/20260305-v2-laneA-sem-phenomxl2-report.md`
    - `docs/reports/20260305-v2-laneB-utm-zwick-report.md`
    - `docs/reports/20260305-v2-laneC-psa-horiba-report.md`
  - Shared runtime did regress for staged plugins under closeout:
    - PSA raw `.ngb` resolves `psa_horiba` but is rejected in `transform` with `reason_code="cannot_process"`.
    - Zwick raw `.zs2` is rejected in `resolve` with `reason_code="processor_not_found"` because current selection still depends on immediate processability.

---

## Section: Cross-plugin runtime proof
- Why this matters: The migration phase is only done when the three plugins work together on the real standalone headless path.

### Checklist
- [x] Re-run runtime smoke for `horiba_blb -> psa_horiba`.
- [x] Re-run runtime smoke for `tischrem_blb -> sem_phenomxl2`.
- [x] Re-run runtime smoke for `zwick_blb -> utm_zwick`.
- [ ] Confirm persisted sqlite payloads reflect plugin-specific behavior.

### Completion Notes
- How it was done:
  - Probe roots:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-tischrem_blb-pn2c1qlt`
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-zwick_blb-usf7mbgl`
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-horiba_blb-q71hmi_l`
  - `tischrem_blb -> sample.tif` succeeded end-to-end:
    - `processed_count=1`
    - `failed_count=0`
    - persisted record `plugin_id="sem_phenomxl2"` and `datatype="img"`
  - `zwick_blb -> series_a.zs2 + series_a.xlsx` failed before persistence:
    - `processed_count=1`
    - `failed_count=1`
    - no records persisted
  - `horiba_blb -> bucket/sentinel batch` failed before persistence:
    - `processed_count=1`
    - `failed_count=1`
    - no records persisted
  - Persisted plugin-specific payloads are therefore only confirmed for the SEM path in this closeout run.

---

## Section: Final gates and report
- Why this matters: The three-plugin phase needs one final measurable quality gate and a written handoff artifact.

### Checklist
- [x] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [x] Run targeted plugin and runtime suites.
- [x] Run `python -m pytest -q tests/dpost_v2`.
- [x] Publish the migration closeout report.

### Completion Notes
- How it was done:
  - Ran `python -m ruff check src/dpost_v2 tests/dpost_v2` and it passed.
  - Ran targeted suites:
    - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py`
    - `tests/dpost_v2/plugins/devices/utm_zwick`
    - `tests/dpost_v2/plugins/devices/psa_horiba`
    - `tests/dpost_v2/runtime/test_composition.py`
    - `tests/dpost_v2/plugins/test_migration_coverage.py`
  - Ran full suite:
    - `python -m pytest -q tests/dpost_v2`
    - result: `415 passed`, `9 failed`
  - Published blocker report:
    - `docs/reports/20260305-v2-three-plugin-closeout-report.md`
