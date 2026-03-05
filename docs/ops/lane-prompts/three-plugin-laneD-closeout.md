You are working the `laneD-closeout` packet for `dpost_v2`.

Goal:
Integrate the three migrated plugins, run cross-plugin validation, and publish the migration closeout.

Allowed edits:
- `tests/dpost_v2/runtime/**`
- `docs/checklists/**`
- `docs/reports/**`

Depends on:
- merged results from `laneA-sem-phenomxl2`
- merged results from `laneB-utm-zwick`
- merged results from `laneC-psa-horiba`

Task:
- re-run cross-plugin runtime smoke
- run final quality gates
- publish migration closeout report

Do not:
- re-open plugin implementation unless blocked by an integration defect

Validation:
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
- targeted runtime or plugin suites
- `python -m pytest -q tests/dpost_v2`

Output:
- files changed
- commands run and results
- cross-plugin findings
- residual risks
