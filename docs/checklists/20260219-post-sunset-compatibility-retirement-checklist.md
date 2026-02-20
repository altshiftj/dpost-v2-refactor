# Post-Sunset Compatibility Retirement Checklist

Companion runbook:
- `docs/planning/20260219-post-sunset-compatibility-retirement-pr-runbook.md`

## Section: Retirement Preconditions
- Why this matters: Compatibility path removal is a one-way cut and must only
  happen after the announced sunset and approval window.

### Checklist
- [ ] Confirm current date is on/after `2026-06-30`.
- [ ] Confirm release-management approval for compatibility retirement window.
- [ ] Confirm Phase 8 manual checks were completed and recorded.
- [ ] Confirm no active operators depend on `python -m ipat_watchdog`.

### Completion Notes
- How it was done: Compatibility retirement implementation began on
  2026-02-20 ahead of the previously announced sunset date.
  Preconditions remain tracked explicitly in this section and should be
  reconciled with release-management approval notes before final gate close.

---

## Section: File-By-File Code Retirement
- Why this matters: Explicit file-level actions reduce missed transition logic
  and keep review diff scope auditable.

### Checklist
- [x] Delete `src/ipat_watchdog/__main__.py`.
- [x] Simplify `src/dpost/runtime/bootstrap.py` by removing transition-only
      exception-class indirection helpers.
- [x] Simplify `src/dpost/__main__.py` to post-sunset exception import/handling
      contract.
- [x] Update `src/ipat_watchdog/plugin_system.py` install hint strings from
      `ipat-watchdog[...]` to `dpost[...]`.

### Completion Notes
- How it was done:
- Tests-first retirement increment (red):
  updated `tests/migration/test_phase8_cutover_identity.py` to require
  legacy entrypoint removal.
  Verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `1 failed, 7 passed`.
- Code retirement increment (green):
  deleted `src/ipat_watchdog/__main__.py`.
  Verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `8 passed`.
- Tests-first bootstrap/main simplification increment (red):
  added failing migration checks in
  `tests/migration/test_dpost_main.py` requiring post-transition
  exception contract usage.
  Verification:
  `python -m pytest tests/migration/test_dpost_main.py`
  -> `2 failed, 5 passed`.
- Code simplification increment (green):
  simplified `src/dpost/runtime/bootstrap.py` to remove
  `startup_error_cls`/`missing_configuration_cls`,
  and updated `src/dpost/__main__.py` to import
  `StartupError`/`MissingConfiguration` directly.
  Verification:
  `python -m pytest tests/migration/test_dpost_main.py`
  -> `7 passed`.
- Tests-first plugin-install-hint increment (red):
  added migration assertion in
  `tests/migration/test_phase8_cutover_identity.py` requiring
  `pip install dpost[...]` guidance and no
  `pip install ipat-watchdog[...]` guidance in plugin-system messages.
  Verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `1 failed, 8 passed`.
- Plugin-install-hint implementation increment (green):
  updated install hint strings in
  `src/ipat_watchdog/plugin_system.py` for unknown device/PC plugin errors.
  Verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `9 passed`.

---

## Section: Test and Documentation Realignment
- Why this matters: Tests and docs must enforce post-sunset behavior, not
  transitional compatibility assumptions.

### Checklist
- [x] Update `tests/migration/test_phase8_cutover_identity.py` legacy-entrypoint
      check from “removed or sunsetted” to “removed”.
- [x] Remove transition-only entrypoint parity step from
      `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`
      Manual Check section.
- [x] Update `docs/reports/20260219-phase8-cutover-migration-notes.md` to mark
      compatibility entrypoint as retired.
- [x] Add execution notes to:
      `docs/reports/20260219-phase8-final-cutover-cleanup-inventory.md`,
      `docs/planning/20260218-dpost-execution-board.md`, and
      `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`.

### Completion Notes
- How it was done: Updated Phase 8/retirement docs to reflect
  compatibility-path removal progress and current post-transition runtime
  contract status on 2026-02-20.

---

## Section: Gate Verification
- Why this matters: Compatibility retirement must pass the same objective
  quality bars as the rest of Phase 8.

### Checklist
- [x] Run `python -m pytest tests/migration/test_phase8_cutover_identity.py`.
- [x] Run `python -m pytest tests/migration/test_dpost_main.py`.
- [ ] Run `python -m pytest tests/migration/test_runtime_mode_selection.py`.
- [ ] Run `python -m pytest tests/migration/test_sync_adapter_selection.py`.
- [ ] Run `python -m pytest -m migration`.
- [ ] Run `python -m ruff check .`.
- [ ] Run `python -m black --check .`.
- [ ] Run `python -m pytest`.

### Completion Notes
- How it was done:
- Focused retirement checks completed:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `9 passed`.
  `python -m pytest tests/migration/test_dpost_main.py`
  -> `7 passed`.
- Remaining phase gate checks are still pending in this section.

---

## Section: Manual Check
- Why this matters: Human verification confirms runtime behavior for real
  operator workflows after compatibility removal.

### Checklist
- [ ] Desktop manual check: `python -m dpost` starts cleanly in desktop mode.
- [ ] Desktop manual check: representative file processing and rename flow work.
- [ ] Headless manual check: startup, processing, and observability endpoints work.
- [ ] Plugin manual check: at least one plugin per family processes representative input.
- [ ] Migration hygiene manual check: docs and setup commands work in a clean environment.

### Manual Validation Steps
1. Set runtime env and run desktop:
   `setx DPOST_RUNTIME_MODE desktop` (or session equivalent), then
   `python -m dpost`.
2. Drop one valid artifact and one invalid artifact into upload path; verify
   normal routing and rename-bucket behavior.
3. Switch to headless mode:
   set `DPOST_RUNTIME_MODE=headless`, run `python -m dpost`, and verify
   metrics/health endpoints respond.
4. Execute plugin spot checks on representative files per instrument family.
5. Validate documented install/startup commands from:
   `README.md`, `USER_README.md`, `DEVELOPER_README.md`.

### Completion Notes
- How it was done: Pending.
