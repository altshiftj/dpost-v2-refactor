# UTM Zwick end-series failure findings (2026-02-16)

## Inputs
- `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114326.csv`
- `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114429.csv`
- `src/ipat_watchdog/device_plugins/utm_zwick/docs/watchdog.log`

## Context
- A lab run executed five experiments that incrementally updated one `.ZS2` file.
- At end-of-series, the device generated an `.xlsx` export.
- Expected behavior: `.ZS2` and `.xlsx` are moved into one record folder.
- Observed behavior: record folder was created, but both artefacts were rejected to exceptions and the raw file appeared missing.

## Findings
- The same `.ZS2` file was updated in five waves and reached `7,722,236` bytes before `.xlsx` creation.
- Processing failed first on `.xlsx`, then on `.ZS2`, with `KeyError: "No staged series for 'LGr-ipat-VCpure_260123_r2r_T85'"`.
- Root cause is series staging key mismatch:
  - Preprocessing stages using a sanitized key (`lgr-ipat-...`).
  - Processing pops using a raw stem key (`LGr-ipat-...`).
- The second exceptions spreadsheet is a mislabeled raw payload:
  - `01_Exceptions/LGr-ipat-VCpure_260123_r2r_T85-02.xlsx` has the same size (`7,722,236`) as the final `.ZS2`.

## Evidence
- Failure event and traceback:
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/watchdog.log:1328`
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/watchdog.log:1336`
- Series staging key creation vs lookup:
  - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py:67`
  - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py:72`
  - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py:142`
  - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py:147`
  - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py:149`
  - `src/ipat_watchdog/core/storage/filesystem_utils.py:381`
  - `src/ipat_watchdog/core/storage/filesystem_utils.py:391`
- Exception move path uses stale extension metadata after effective-path fallback:
  - `src/ipat_watchdog/core/processing/file_process_manager.py:132`
  - `src/ipat_watchdog/core/processing/file_process_manager.py:139`
  - `src/ipat_watchdog/core/processing/file_process_manager.py:411`
- Filewatch ordering and destinations:
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114326.csv`
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114429.csv`

## Risks
- Mixed-case prefixes can repeatedly fail end-of-series processing.
- Operators can misinterpret data location because raw files may be moved with wrong extensions.
- Repeated requeue/stability loops can delay finalization and increase operational confusion.

## Open Questions
- Was the `.ZS2` permanently deleted in this incident?
  - Answer: No evidence of permanent loss in the trace set; it was moved to exceptions as `...-02.xlsx`.
- Why was a record folder created even though processing failed?
  - Answer: Record creation occurs before `device_specific_processing`; failure happened at staged-series retrieval time.
