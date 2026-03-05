# 20260305 V2 Three-Plugin Parallel Lanes RPC

## Objective

Parallelize the post-handshake functional migration for:
- `sem_phenomxl2`
- `utm_zwick`
- `psa_horiba`

without reopening shared runtime-wiring seams.

## Preconditions

- Runtime handshake is closed in `docs/reports/20260305-v2-handshake-closeout-report.md`.
- Active functional target is tracked in `docs/checklists/20260305-v2-three-plugin-functional-parity-checklist.md`.
- Manual probe matrix is already green for:
  - `horiba_blb -> psa_horiba`
  - `tischrem_blb -> sem_phenomxl2`
  - `zwick_blb -> utm_zwick`

## Parallelization Strategy

Use five lanes:

1. `lane0-spec-lock`
- centralize parity extraction from `src/ipat_watchdog/device_plugins/**`
- create red parity-spec tests
- publish accepted/deferred behavior matrix

2. `laneA-sem-phenomxl2`
- implement SEM parity only

3. `laneB-utm-zwick`
- implement Zwick parity only

4. `laneC-psa-horiba`
- implement PSA parity only

5. `laneD-closeout`
- integrate runtime smoke updates
- run cross-plugin gates
- publish migration closeout report

## Ownership Rules

### Shared-only lane

Only `lane0-spec-lock` and `laneD-closeout` may edit shared docs or shared runtime-closeout surfaces.

### Plugin lanes

`laneA-sem-phenomxl2` allowed scope:
- `src/dpost_v2/plugins/devices/sem_phenomxl2/**`
- `tests/dpost_v2/plugins/devices/sem_phenomxl2/**`
- plugin-specific runtime smoke additions only if pre-approved into lane packet

`laneB-utm-zwick` allowed scope:
- `src/dpost_v2/plugins/devices/utm_zwick/**`
- `tests/dpost_v2/plugins/devices/utm_zwick/**`

`laneC-psa-horiba` allowed scope:
- `src/dpost_v2/plugins/devices/psa_horiba/**`
- `tests/dpost_v2/plugins/devices/psa_horiba/**`

## Shared Files To Avoid In Plugin Lanes

These should remain centralized unless explicitly split first:
- `src/dpost_v2/runtime/**`
- `src/dpost_v2/application/ingestion/**`
- `tests/dpost_v2/runtime/test_composition.py`
- `docs/checklists/**`
- `docs/reports/**`

## Merge Order

1. `lane0-spec-lock`
2. `laneA-sem-phenomxl2`
3. `laneB-utm-zwick`
4. `laneC-psa-horiba`
5. `laneD-closeout`

## Exit Criteria

- parity-spec tests exist for all three plugins
- each plugin lane is green on its targeted tests
- full `tests/dpost_v2` suite is green after integration
- closeout report documents accepted behavior, deferred gaps, and residual risks

## Companion Docs

- Coordination checklist:
  - `docs/checklists/20260305-v2-three-plugin-parallel-coordination-checklist.md`
- Lane checklists:
  - `docs/checklists/20260305-v2-three-plugin-lane0-spec-lock-checklist.md`
  - `docs/checklists/20260305-v2-three-plugin-laneA-sem-phenomxl2-checklist.md`
  - `docs/checklists/20260305-v2-three-plugin-laneB-utm-zwick-checklist.md`
  - `docs/checklists/20260305-v2-three-plugin-laneC-psa-horiba-checklist.md`
  - `docs/checklists/20260305-v2-three-plugin-laneD-closeout-checklist.md`
- Lane prompts:
  - `docs/ops/lane-prompts/three-plugin-5-launch-pack.md`
