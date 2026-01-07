# Hioki CC/Aggregate Forced Uploads (Checklist)

## Scope and assumptions
- [ ] Confirm Hioki outputs: cumulative CC, cumulative aggregate, per-measurement files.
- [ ] Confirm CC/aggregate should overwrite in record and be force-uploaded each measurement.
- [ ] Decide aggregate handling: force overwrite vs snapshot per measurement.
- [ ] Decide overwrite strategy: in-place replace vs copy-then-rename.

## Design choice
- [x] Use `ProcessingOutput.force_paths` to signal forced uploads.
- [x] Decide helper location for force marking: reuse `LocalRecord.mark_file_as_unsynced`.
- [x] Define deterministic CC/aggregate filenames (e.g., `<file_id>-cc.csv`, `<file_id>-results.csv`).

## Core changes
- [x] Add `force_paths: tuple[str, ...] = ()` to `ProcessingOutput`.
- [x] In `FileProcessManager.add_item_to_record`, after normal `update_record`:
  - [x] Register each existing force path.
  - [x] Mark each force path unsynced so Kadi uploads with `force=True`.
- [x] Add a small helper to mark a path as unsynced + force-required (reuse `LocalRecord.mark_file_as_unsynced`).

## Hioki processor changes
- [x] Normalize measurement prefix to base sample ID (strip timestamp / CC_).
- [x] Copy/overwrite CC and aggregate into the record with deterministic names.
- [x] Return `ProcessingOutput` with `force_paths` set to CC/aggregate paths.
- [x] Keep measurement files unique per measurement.

## Tests
- [x] Add tests for `force_paths` registration and force-marking.
- [x] Add a Hioki processor test covering overwrite + force behavior.
- [x] Verify Kadi sync uses `force=True` for forced paths.

## Documentation
- [ ] Update `decisionlog.md` after implementation.
