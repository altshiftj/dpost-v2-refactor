# Decision Log

## 2026-01-07 - Forced uploads for cumulative Hioki files
- **Context:** Hioki exports cumulative CC and aggregate files that must be overwritten in the record and re-uploaded without forcing every other artefact.
- **Decision:** Added `ProcessingOutput.force_paths` so processors can request forced uploads for specific paths, with `FileProcessManager` registering and marking those paths unsynced (relative paths resolve against the record directory).
- **Impact:** CC and aggregate files can overwrite in place and re-upload with `force=True` while leaving other record files untouched.

## 2026-01-07 - Safe-save reappearance resolution
- **Context:** Excel safe-save can delete the original path before it reappears, causing device resolution to defer indefinitely without stability checks.
- **Decision:** When a path is missing, `DeviceResolver` selects a candidate device that advertises a non-zero `reappear_window_seconds` so `FileStabilityTracker` can wait for the file to return.
- **Impact:** Safe-save sequences complete successfully without sending artefacts to exceptions.

## 2025-12-03 - SEM temp-folder deferral
- **Context:** SEM Phenom XL2 exports build ELID folders via `_old/_new_<suffix>` temp directories that appear in the watch path before the final folder exists. These triggered `Invalid file type` rejections because routing inspected them too early.
- **Decision:** Introduced a defer path so temp directories are ignored until their final name appears.
  - Added `DeviceConfig.should_defer_dir` to detect staging folders via `watcher.temp_folder_regex`.
  - Updated `ConfigService.matching_devices`/`deferred_devices`, `DeviceResolver`, and `_ProcessingPipeline._prepare_request` to mark such folders as `ProcessingStatus.DEFERRED` instead of invalid.
  - Confirmed `FileStabilityTracker` already skips temp-pattern files, so the final routed folder still passes stability checks normally.
- **Impact:** SEM temp folders no longer trigger user-facing rejections; the watcher simply re-polls until the finished folder exists, keeping the stability guard intact for real processing.

## 2025-12-05 – SEM resolver deferrals
  - Added early existence checks and `_should_defer_empty_directory` guard to emit deferred resolutions with clear reasons.
  - `_ProcessingPipeline._prepare_request` already interprets the deferred flag, so the pipeline now waits instead of moving items to exceptions.
  - Hardened the SEM watcher regex to `_ (old|new)
- **Impact:** Transient SEM folders are retried automatically until the final artefacts appear, eliminating premature rejections and exception moves.
## 2025-12-05 – Deferred retry scheduling
- **Context:** Deferred folders were never re-processed, causing completed SEM exports to linger in the watch directory.
- **Decision:** Implemented device-configurable retry scheduling for deferred items.
  - Added `retry_delay_seconds` to `WatcherSettings` and propagate per-device delays through `DeviceResolution` and `ProcessingResult`.
  - Updated `DeviceWatchdogApp` to re-queue deferred paths using the provided delay, defaulting to the PC watcher setting.
  - Ensured unit coverage for resolver and processing manager changes.
- **Impact:** Deferred artefacts are automatically retried at device-appropriate intervals until ready, while temp folders still defer without generating noise.

## 2025-12-06 - Retry guard for vanished paths
- **Context:** SEM temp folders disappear after export finalization; retries kept cycling stale paths.
- **Decision:** Added existence check before re-queueing deferred items in `DeviceWatchdogApp`.
  - Only enqueue if the path still exists; otherwise log `DEBUG` and stop the retry cycle.
- **Impact:** Eliminates endless retries on removed temp folders; keeps logs clean and processing focused on live artefacts.

## 2025-12-06 - Device drop tracing utility
- **Context:** Onboarding new instruments required insight into which files/folders appear (and when) in watch directories before a plugin exists. Manual observation was error-prone and provided no timing data for `WatcherSettings`.
- **Decision:** Created `src/ipat_watchdog/tools/device_drop_tracer.py`, a standalone watchdog observer that recursively records create/modify/move/delete events with timestamps, parent/depth info, and lightweight file hashes.
  - Emits JSONL traces plus burst summaries (gap-based grouping) to `<watch_dir>/.watchdog_traces` and documents usage in `DEVELOPER_README.md`.
  - Tool currently expects a Python runtime (same dependency stack as developers); production deployment will require bundling/packaging work.
- **Impact:** Provides repeatable visibility into device IO patterns so new plugins and watcher settings can be tuned confidently before integrating with the main processing pipeline.
