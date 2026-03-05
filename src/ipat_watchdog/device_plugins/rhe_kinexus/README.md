# RHE Kinexus file processor

Pairs Kinexus Pro+ native project files (.rdf) with exported results (.csv), stages them atomically, archives the native file, and moves both artefacts into the target record folder.

## What it does
- Detects candidate files via `probe_file()`:
  - Native `.rdf` → marked unknown (binary; skip content probe)
  - Export `.csv` → text prefix scan for Kinexus markers (e.g., "kinexus", "rspace").
- Preprocessing waits until raw+export are both present (same basename) and stages them in a `.__staged__` directory for atomic processing. The preprocessing hook returns a `PreprocessingResult` with `effective_path` set to the staging directory.
- Processing:
  - Archives the native `.rdf` to `<base>.zip`.
  - Moves the export to `<base>.csv` in the record directory.
- Returns `ProcessingOutput(final_path=<record dir>, datatype="rhe")`.

Main class: `FileProcessorRHEKinexus` (see `file_processor.py`). Device wiring: `RheKinexusPlugin` (see `plugin.py`).

## Contract (summary)
- Input: `src_path` (staged dir from preprocessing `effective_path`), `record_path`, `filename_prefix`, `extension` (ignored for staged processing)
- Behavior:
  - `device_specific_preprocessing(...)` returns a `PreprocessingResult` with `effective_path` pointing at the staged dir.
  - `device_specific_preprocessing(path)` → pair `.rdf` + `.csv` sharing the same stem; auto-rename cross-stem arrivals; stage together.
  - `probe_file(path)` → for `.csv`, content-heuristic match; for `.rdf`, unknown.
  - `is_appendable(...)` → Always `True` (exports append to an existing record series).
  - `device_specific_processing(...)` → produce `<base>.zip` + `<base>.csv` in `record_path`.
- Output: `ProcessingOutput(final_path=<record dir>, datatype="rhe")`.

## Configuration
Built-in device config (see `settings.py`):
- `identifier`: `"rhe_kinexus"`
- `files.native_extensions`: `{ ".rdf" }`
- `files.exported_extensions`: `{ ".csv" }`  (extendable to `.txt`/`.pdf` if you also adjust the processor)
- `metadata.device_abbr`: `"RHE"`, `record_tags`: `["Rheology"]`
- Watcher/session defaults: short poll, small stabilization window, 600s session timeout.

If your deployment uses a user config file, ensure the Kinexus device entry points to the correct input folder and (optionally) extends `exported_extensions` to match your rSpace exports.

## File handling details
- Staging directory: `<stem>.__staged__` (unique-suffixed if needed) created next to inputs; cleaned when empty.
- Name allocation: uses `get_unique_filename(...)` and a device-wide ID separator to avoid collisions; ensures `<base>.csv` and `<base>.zip` are unique pairs.
- Orphan cleanup: incomplete pairs are purged to the exception folder after a TTL (~900s by default).
- Probe negatives: CSVs containing unrelated markers (e.g., Zwick, Horiba) reduce confidence and may be marked `unknown`.

## Integration notes
- Plugin id: `rhe_kinexus` (registered via `register_device_plugins`).
- Logging via `setup_logger(__name__)` follows repository settings.
- Downstream consumers can treat `datatype="rhe"` as a rheology bundle (`<base>.csv` + `<base>.zip`).

## Quick manual test
1. Drop `test.rdf` and `test.csv` (same stem) into the Kinexus input folder.
2. Observe a `test.__staged__/` appear briefly, then files move to the record directory as:
   - `RHE-<...>.csv`
  - `RHE-<...>.zip`
3. Verify the record directory contains both files and the pipeline reports `datatype="rhe"`.

## When to modify this processor
- Different export format(s) (e.g., `.txt`) → add to `exported_extensions` and extend probe/processing as needed.
- Need to retain raw `.rdf` unzipped → remove the archive step or store both.
- If output type changes → update `datatype` in the returned `ProcessingOutput`.
