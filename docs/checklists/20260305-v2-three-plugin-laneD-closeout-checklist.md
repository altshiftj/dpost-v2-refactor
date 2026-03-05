# Checklist: Lane D Closeout

## Section: Integration intake
- Why this matters: Closeout should start from committed plugin-lane results, not speculative expectations.

### Checklist
- [x] Confirm `laneA`, `laneB`, and `laneC` are integrated for closeout.
- [x] Review plugin-lane deferred-risk notes.
- [x] Confirm shared runtime surfaces did not regress during lane integration.

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
  - Shared runtime regression for staged plugins was closed in the follow-on seam slice:
    - `docs/reports/20260305-v2-staged-runtime-seam-report.md`

---

## Section: Cross-plugin runtime proof
- Why this matters: The migration phase is only done when the three plugins work together on the real standalone headless path.

### Checklist
- [x] Re-run runtime smoke for `horiba_blb -> psa_horiba`.
- [x] Re-run runtime smoke for `tischrem_blb -> sem_phenomxl2`.
- [x] Re-run runtime smoke for `zwick_blb -> utm_zwick`.
- [x] Confirm persisted sqlite payloads reflect plugin-specific behavior.

### Completion Notes
- How it was done:
  - Re-ran runtime proof under real `compose_runtime(...)` headless execution.
  - Verified:
    - `tischrem_blb -> sample.tif` persists `plugin_id="sem_phenomxl2"` and `datatype="img"`
    - `zwick_blb -> sample.zs2 + sample.xlsx` defers the pre-event and persists `plugin_id="utm_zwick"`
    - `horiba_blb -> bucket/sentinel batch` defers staged pre-events and persists `plugin_id="psa_horiba"`
  - Persisted payloads now reflect plugin-specific processor behavior including normalized staged artifact paths.

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
    - `tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py`
    - `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`
    - `tests/dpost_v2/application/ingestion/test_pipeline_integration.py`
    - `tests/dpost_v2/application/ingestion/test_engine.py`
    - `tests/dpost_v2/application/contracts/test_events.py`
    - `tests/dpost_v2/application/runtime/test_dpost_app.py`
    - `tests/dpost_v2/runtime/test_composition.py`
    - `tests/dpost_v2/plugins/test_migration_coverage.py`
  - Ran full suite:
    - `python -m pytest -q tests/dpost_v2`
    - result: `429 passed`
  - Published closeout artifacts:
    - `docs/reports/20260305-v2-staged-runtime-seam-report.md`
    - `docs/reports/20260305-v2-three-plugin-closeout-report.md`
