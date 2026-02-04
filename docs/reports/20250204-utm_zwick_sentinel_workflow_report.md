# Report Template

## Title
- UTM Zwick sentinel workflow assessment

## Date
- 2026-02-04

## Context
- Requested change: replace `.csv`/`.txt`-driven processing with `.zs2` + sentinel `.xlsx` workflow keyed by `usr-inst-sample_name`.

## Findings
- Current preprocessing releases series only when a `.csv` appears.
- `.xlsx` is listed in config but not handled by the processor.
- Tests assume `.csv` triggers processing and `.txt` snapshots are persisted.

## Evidence
- Processor logic: [src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py](src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py)
- Device config: [src/ipat_watchdog/device_plugins/utm_zwick/settings.py](src/ipat_watchdog/device_plugins/utm_zwick/settings.py)
- Unit tests: [tests/unit/device_plugins/utm_zwick/test_file_processor.py](tests/unit/device_plugins/utm_zwick/test_file_processor.py)

## Risks
- Filename prefixes must still satisfy core record-routing rules; invalid `usr-inst-sample_name` would break record creation.
- Sentinel naming rules are undefined; mismatches could strand `.zs2` data.
- Existing tests and integrations will fail once the trigger switches to `.xlsx`.

## Open Questions
- Is the sentinel `.xlsx` expected to share the exact prefix with the `.zs2`?
  - Answer: Yes, exact prefix match is required.
- Should incomplete `.zs2` series flush on session end when no sentinel appears?
  - Answer: Enforce a 30-minute TTL; process `.zs2` into a record and sync when TTL expires.
- What should be the primary `datatype` for the record (`xlsx` vs `zs2`)?
  - Answer: `xlsx`.
