# Phase 8 Final Cutover and Cleanup Inventory

## Date
- 2026-02-19

## Context
- Phase 7 is closed and green.
- Phase 8 starts with an inventory-first pass and tests-first cutover contract
  for canonical `dpost` project identity and compatibility retirement
  expectations before implementation.

## Inventory Scope
- Packaging and entrypoint identity:
  - `pyproject.toml`
  - `src/dpost/__main__.py`
  - `src/ipat_watchdog/__main__.py`
  - `src/dpost/runtime/composition.py`
- Canonical docs/startup naming:
  - `README.md`
  - `USER_README.md`
  - `DEVELOPER_README.md`
- Script/deployment naming and namespace wiring:
  - `scripts/infra/windows/consolidated_pipelines/pipeline-utils.ps1`
  - `scripts/infra/windows/consolidated_pipelines/README.md`
  - `scripts/infra/windows/consolidated_pipelines/01-test.ps1`
  - `scripts/infra/windows/consolidated_pipelines/02-build.ps1`
  - `scripts/infra/windows/consolidated_pipelines/validate-config.ps1`

## Findings
| Area | Observation | Evidence |
|---|---|---|
| Packaging canonical identity | Project metadata remains legacy-first (`name = "ipat-watchdog"`) and scripts still expose both legacy and new entrypoints. | `pyproject.toml` (`[project] name`, `[project.scripts] ipat-watchdog + dpost`) |
| README canonical naming | Top-level README still presents migration framing and explicitly advertises the legacy entrypoint mapping. | `README.md` header + startup bullets |
| User/developer startup docs | Operator/developer startup instructions still reference `python -m ipat_watchdog` and `ipat-watchdog` script names. | `USER_README.md` environment/startup table; `DEVELOPER_README.md` run section |
| Script namespace cutover | Windows consolidated pipeline scripts/docs still hardcode `ipat_watchdog` namespaces (entry-point group + module paths). | `scripts/infra/windows/consolidated_pipelines/pipeline-utils.ps1`; `scripts/infra/windows/consolidated_pipelines/README.md`; additional `src\\ipat_watchdog\\...` references in build/validation scripts |
| Compatibility retirement posture | Legacy entrypoint is still a fully active CLI module with no explicit deprecation/sunset note; `dpost` runtime still directly imports/delegates to legacy bootstrap modules. | `src/ipat_watchdog/__main__.py`, `src/dpost/__main__.py`, `src/dpost/runtime/composition.py` |

## Phase 8 Tests-First Contract Added
- Added migration tests in:
  - `tests/migration/test_phase8_cutover_identity.py`
- New failing expectations cover:
  - canonical `dpost` package metadata and console script identity in
    `pyproject.toml`
  - canonical startup naming in README/user/developer docs
  - script namespace cutover away from hardcoded `ipat_watchdog` identifiers in
    consolidated pipeline scripts/docs
  - legacy compatibility retirement expectations:
    - legacy entrypoint removed or explicitly deprecated with a dated sunset
    - `dpost` entrypoint/composition no longer directly import/delegate
      legacy bootstrap paths

## Red-State Verification
- `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `8 failed`
- `python -m pytest -m migration`
  -> `8 failed, 71 passed, 302 deselected`

## Risks
- Canonical identity cutover touches packaging, documentation, and deployment
  scripts at once; unsequenced changes can break install/run/deploy workflows.
- Compatibility retirement without explicit guards can leave hidden
  `ipat_watchdog` dependencies in runtime composition and release scripts.

## Open Questions
- If any legacy entrypoint path is retained temporarily, what explicit sunset
  date should be documented?
  - Answer: Deferred to implementation increment; tests require either removal
    or an explicit deprecation + ISO-date sunset notice.
- Should script migration use new entry-point groups or resolve plugin metadata
  through a non-entry-point registry path?
  - Answer: Deferred to implementation increment; tests currently lock removal
    of hardcoded legacy `ipat_watchdog` script namespaces.

## Update Addendum (2026-02-19)
- Implemented first Phase 8 cutover increment and moved the new migration
  contract to green by:
  - switching canonical packaging identity to `dpost` in `pyproject.toml`
    (`[project].name`) and retiring the `ipat-watchdog` console script entry
  - updating canonical startup naming in `README.md`, `USER_README.md`, and
    `DEVELOPER_README.md` (`python -m dpost` / `dpost`)
  - updating consolidated Windows pipeline docs/scripts away from hardcoded
    legacy namespace usage in:
    `scripts/infra/windows/consolidated_pipelines/pipeline-utils.ps1` and
    `scripts/infra/windows/consolidated_pipelines/README.md`
  - introducing a `dpost` runtime bootstrap bridge
    (`src/dpost/runtime/bootstrap.py`) and routing
    `src/dpost/__main__.py` + `src/dpost/runtime/composition.py` through the
    bridge to avoid direct legacy bootstrap imports in canonical entry modules
  - adding explicit legacy entrypoint deprecation + sunset notice in
    `src/ipat_watchdog/__main__.py` (sunset: `2026-06-30`)
- Follow-up stability fix (same day):
  - refactored the bootstrap bridge to resolve legacy bootstrap symbols lazily
    per call so migration tests can monkeypatch bootstrap paths reliably and
    avoid runtime-mode test hangs/timeouts from unintended real startup calls
- Verification after implementation and bridge fix:
  - `python -m pytest tests/migration/test_phase8_cutover_identity.py`
    -> `8 passed`
  - `python -m pytest tests/migration/test_runtime_mode_selection.py`
    -> `8 passed`
  - `python -m pytest tests/migration/test_sync_adapter_selection.py`
    -> `9 passed`
  - `python -m pytest -m migration`
    -> `79 passed, 302 deselected`
