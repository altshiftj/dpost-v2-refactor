# Decision Log

## 2025-12-03 – SEM temp-folder deferral
- **Context:** SEM Phenom XL2 exports build ELID folders via `_old/_new_<suffix>` temp directories that appear in the watch path before the final folder exists. These triggered `Invalid file type` rejections because routing inspected them too early.
- **Decision:** Introduced a defer path so temp directories are ignored until their final name appears.
  - Added `DeviceConfig.should_defer_dir` to detect staging folders via `watcher.temp_folder_regex`.
  - Updated `ConfigService.matching_devices`/`deferred_devices`, `DeviceResolver`, and `_ProcessingPipeline._prepare_request` to mark such folders as `ProcessingStatus.DEFERRED` instead of invalid.
  - Confirmed `FileStabilityTracker` already skips temp-pattern files, so the final routed folder still passes stability checks normally.
- **Impact:** SEM temp folders no longer trigger user-facing rejections; the watcher simply re-polls until the finished folder exists, keeping the stability guard intact for real processing.

## 2025-12-05 – SEM resolver deferrals
- **Context:** Empty SEM folders and disappearing `_new` directories were still being rejected before contents stabilized.
- **Decision:** Updated `DeviceResolver` to defer when the path vanishes mid-resolution or when a directory is empty but expected to gain contents.
  - Added early existence checks and `_should_defer_empty_directory` guard to emit deferred resolutions with clear reasons.
  - `_ProcessingPipeline._prepare_request` already interprets the deferred flag, so the pipeline now waits instead of moving items to exceptions.
  - Hardened the SEM watcher regex to `_ (old|new)
    ` suffixes (case-insensitive) so only staging folders are deferred.
- **Impact:** Transient SEM folders are retried automatically until the final artefacts appear, eliminating premature rejections and exception moves.
