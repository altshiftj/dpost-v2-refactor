# Post-Sunset Compatibility Retirement PR Runbook

## Purpose
- Provide a ready-to-execute PR package after `2026-06-30` for retiring
  transition-only compatibility paths.

## PR Title
- `phase8: retire post-sunset ipat_watchdog compatibility paths`

## PR Body Template
```markdown
## Summary
- Retire transition-only `ipat_watchdog` compatibility entrypoint and related bridge indirection after the announced sunset date (`2026-06-30`).
- Keep canonical `dpost` runtime behavior unchanged for desktop/headless paths.

## Changes
- Deleted `src/ipat_watchdog/__main__.py` (expired compatibility entrypoint).
- Simplified `src/dpost/runtime/bootstrap.py` post-transition API surface.
- Simplified `src/dpost/__main__.py` to post-sunset exception handling contract.
- Updated legacy naming hints in `src/ipat_watchdog/plugin_system.py` (`ipat-watchdog[...]` -> `dpost[...]`).
- Updated migration tests/docs/checklists to enforce post-sunset expectations.

## Sunset/Approval
- Sunset threshold confirmed: on/after `2026-06-30`.
- Compatibility retirement approval: <link ticket/approval note>.

## Validation
- `python -m pytest tests/migration/test_phase8_cutover_identity.py`
- `python -m pytest tests/migration/test_dpost_main.py`
- `python -m pytest tests/migration/test_runtime_mode_selection.py`
- `python -m pytest tests/migration/test_sync_adapter_selection.py`
- `python -m pytest -m migration`
- `python -m ruff check .`
- `python -m black --check .`
- `python -m pytest`

## Manual Validation
- Desktop startup + processing + rename flow.
- Headless startup + processing + observability endpoints.
- Plugin spot checks and setup/docs command verification in clean environment.

## Risks
- Potential hidden operator dependence on `python -m ipat_watchdog`.
- Mitigated via pre-removal confirmation and post-merge runtime checks.
```

## Commit Sequence
1. Retirement preconditions checkpoint:
   - confirm date and approval in checklist docs.
2. Code retirement commit:
   - delete legacy entrypoint and simplify runtime bridge/main.
3. Test contract commit:
   - enforce post-sunset expectations in migration tests.
4. Docs/checklist/execution-board alignment commit:
   - update migration notes and Phase 8 tracking.

## Suggested Commit Messages
1. `phase8: confirm post-sunset compatibility retirement preconditions`
2. `phase8: remove legacy ipat_watchdog entrypoint and simplify runtime bridge`
3. `phase8: enforce post-sunset cutover expectations in migration tests`
4. `phase8: update retirement notes and phase tracking artifacts`

## Command Block: Pre-PR Snapshot
```powershell
python -m pytest tests/migration/test_phase8_cutover_identity.py
python -m pytest tests/migration/test_dpost_main.py
python -m pytest tests/migration/test_runtime_mode_selection.py
python -m pytest tests/migration/test_sync_adapter_selection.py
python -m pytest -m migration
python -m ruff check .
python -m black --check .
python -m pytest
```

## Command Block: Git Sequence
```powershell
git checkout -b phase8/post-sunset-compatibility-retirement

# Commit 1: preconditions/docs checkpoint
git add docs/checklists/20260219-post-sunset-compatibility-retirement-checklist.md
git commit -m "phase8: confirm post-sunset compatibility retirement preconditions"

# Commit 2: code retirement
git add src/ipat_watchdog/__main__.py src/dpost/runtime/bootstrap.py src/dpost/__main__.py src/ipat_watchdog/plugin_system.py
git commit -m "phase8: remove legacy ipat_watchdog entrypoint and simplify runtime bridge"

# Commit 3: tests
git add tests/migration/test_phase8_cutover_identity.py tests/migration/test_dpost_main.py
git commit -m "phase8: enforce post-sunset cutover expectations in migration tests"

# Commit 4: docs/tracking alignment
git add docs/reports/20260219-phase8-cutover-migration-notes.md docs/reports/20260219-phase8-final-cutover-cleanup-inventory.md docs/checklists/20260218-dpost-architecture-tightening-checklist.md docs/planning/20260218-dpost-execution-board.md
git commit -m "phase8: update retirement notes and phase tracking artifacts"
```

## Merge Checklist
- [ ] PR description populated from template above.
- [ ] Validation command outputs attached to PR.
- [ ] Manual validation evidence attached.
- [ ] Sunset and approval references linked.
- [ ] Phase 8 checklist and execution board marked complete for compatibility
      retirement item.
