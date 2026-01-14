# Hioki live run findings (2026-01-14)

## Inputs
- `src/ipat_watchdog/device_plugins/erm_hioki/docs/filewatch_20260114_183632.csv` (Upload folder events)
- `src/ipat_watchdog/device_plugins/erm_hioki/docs/filewatch_20260114_183725.csv` (Data folder events)
- `src/ipat_watchdog/device_plugins/erm_hioki/docs/watchdog.log`

## Preferred flow (as stated)
- CC arrives -> moved into record and synced.
- Measurement arrives -> moved into record as `{file_id}-##.csv` and synced.
- Aggregate arrives -> moved into record as `{file_id}-results.csv` and synced.
- Subsequent runs with same name overwrite CC and results, and force-sync.

## Observed flow
Upload folder (`filewatch_20260114_183632.csv`):
- 18:38:53 CC created (`CC_jfi-ipat-hioki_test.csv`).
- 18:39:15 measurement created (`jfi-ipat-hioki_test_20260114183851.csv`), deleted at 18:39:17.
- 18:39:21 aggregate created (`jfi-ipat-hioki_test.csv`).
- 18:39:43 CC changed (size 830).
- 18:40:05 measurement created (`jfi-ipat-hioki_test_20260114183941.csv`).
- 18:40:12 aggregate changed (size 1139).
- 18:40:24 CC changed (size 1137).
- 18:40:46 measurement created (`jfi-ipat-hioki_test_20260114184022.csv`).
- 18:40:57 aggregate changed (size 1390).

Data folder (`filewatch_20260114_183725.csv`):
- 18:38:55 CC created: `ERM-hioki_test-cc.csv`.
- 18:39:17 measurement created: `ERM-hioki_test-01.csv`.
- 18:39:22 results created: `ERM-hioki_test-results.csv`.
- 18:40:07 results changed (no `-02` created).
- 18:40:48 results changed (no `-03` created).

Watchdog log (`watchdog.log`):
- CC processed and uploaded at 18:38:54/18:38:59.
- Measurement `...-01.csv` processed and uploaded at 18:39:16/18:39:19.
- Results processed and uploaded at 18:39:22/18:39:25.
- Later events show:
  - 18:40:06: processed `...\\Upload\\jfi-ipat-hioki_test.csv -> ...-results.csv`.
  - 18:40:47: processed `...\\Upload\\jfi-ipat-hioki_test.csv -> ...-results.csv`.
- No log entries for `...-02.csv` or `...-03.csv`.
- No log entries showing CC reprocessing after the initial CC or the first measurement.

## Mismatch vs preferred flow
- Only the first measurement becomes a distinct `{file_id}-01.csv`. Later measurements do not produce `{file_id}-02.csv` / `{file_id}-03.csv`.
- Aggregate updates are processed at measurement timestamps, not at the time the aggregate file changes.
- CC updates after the initial CC are not processed on their own; they are only re-copied if a later event happens to trigger it.

## Likely cause (from current pipeline behavior)
- `device_specific_preprocessing()` normalizes the timestamped measurement name to the base name (e.g., `jfi-ipat-hioki_test.csv`).
- In `FileProcessManager`, if that preprocessed path exists, it becomes the effective path.
- Once the aggregate file exists in Upload, later measurement events resolve to the aggregate path (since it already exists).
- Result: the measurement event ends up processing the aggregate file, and the actual timestamped measurement file is skipped.

## Suggested TDD targets (next step)
- Ensure a timestamped measurement is still processed as a measurement even when the aggregate file exists.
- Ensure `{file_id}-02.csv` / `{file_id}-03.csv` are created for later measurement events.
- Decide whether CC/aggregate should be reprocessed on file change events or only via explicit measurement/CC arrivals, then test for that behavior.
