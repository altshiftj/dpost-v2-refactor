# EXTR Haake file processor

Moves Mischraum extruder Excel exports into the target record folder, ensuring unique filenames and marking the output as tabular data.

## What it does
- Detects candidate files by extension via `probe_file()` and the device's `allowed_extensions` setting.
- Always treats files as appendable to an existing record via `is_appendable()`.
- Moves the file into the record directory using a unique name with `get_unique_filename(...)` and `move_item(...)` in `device_specific_processing()`.
- Returns `ProcessingOutput` with `datatype="tabular"`.

Main class: `FileProcessorEXTRHaake` (see `file_processor.py`).

## Contract (summary)
- Input: `src_path`, `record_path`, `filename_prefix`, `extension`
- Behavior:
  - `probe_file(path)` → Match if `Path(path).suffix.lower()` ∈ `device_config.files.allowed_extensions`.
  - `is_appendable(...)` → Always `True`.
  - `device_specific_processing(...)` → Move to `record_path` with a unique filename.
- Output: `ProcessingOutput(final_path=<moved file>, datatype="tabular")`.

## Configuration
The processor reads allowed extensions from the device config. Ensure the EXTR Haake device has the proper list, e.g.:

```toml
[devices.extr_haake.files]
allowed_extensions = [".xls", ".xlsx", ".csv"]
```

Adjust to match the actual export format used by the Mischraum extruder.

## File handling details
- Unsupported file extensions → `probe_file()` returns a mismatch and the file is ignored by this processor.
- Name collisions → Resolved automatically by `get_unique_filename(...)`.
- Data type → Marked as `tabular` for downstream consumers.

## Integration notes
- The plugin is located in this folder; the processor is invoked by the common processing pipeline.
- Logging is configured through `setup_logger(__name__)` (core logging). Use repository-wide logging settings to control output.

## Quick manual test
1. Configure `allowed_extensions` to include your test file's extension.
2. Drop a matching Excel export into the watched input folder for the EXTR Haake device.
3. Verify the file appears under the device's record directory, renamed uniquely if needed, and recognized as `tabular`.

## When to modify this processor
- New/changed export extensions → update `allowed_extensions`.
- Different handling (e.g., parsing instead of moving) → extend `device_specific_processing()` accordingly.
- If output type changes → update `datatype` in the returned `ProcessingOutput`.
