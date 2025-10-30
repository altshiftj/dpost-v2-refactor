# PSA Horiba file processor

This plugin pairs native Horiba NGB files with their exported CSV/TSV counterparts and finalizes them in a batch once a sentinel CSV→NGB sequence is observed. It then moves CSVs as-is (no delimiter conversion) and zips each NGB into a ZIP that contains a renamed `.ngb` entry.

The implementation lives in `file_processor.py` as `FileProcessorPSAHoriba` and integrates with the generic pipeline via the FileProcessorABS hooks.

## What it does

- Watches a folder for Horiba outputs: `.ngb` (native) and `.csv`/`.tsv` (exported).
- Buckets NGB→CSV pairs until a “sentinel” CSV is followed by an NGB. That NGB triggers the flush of the entire bucket, including the sentinel pair itself.
- Finalization per pair:
  - Move the CSV to the record folder as `<prefix><sep>NN.csv`.
  - Zip the NGB to `<prefix><sep>NN.zip` with archive member `<prefix><sep>NN.ngb`, then delete the original `.ngb`.
- The `<prefix>` comes from the CSV metadata field `Probenname` (not sanitized here; the core pipeline sanitizes later). `<sep>` is the configured ID separator.

## Processing model (state machine)

Per source folder, the processor tracks transient state:

- `pending_ngb` (queue): NGBs waiting for their CSV (native → exported order).
- `bucket` (list of pairs): paired CSV+NGB waiting for sentinel to finalize.
- `sentinel` (optional): a CSV seen without a pending NGB (exported → native order). When a subsequent NGB arrives, it becomes the sentinel NGB and triggers finalization using the sentinel CSV’s `Probenname` as the batch prefix.
- `finalizing` (internal): batches keyed by a staging folder path created when the sentinel NGB arrives (details below).

Arrival logic:

- CSV arrives while there is a queued `pending_ngb` → pair them and add to `bucket`.
- CSV arrives with no pending NGB → remember it as `sentinel` and wait for the next NGB.
- NGB arrives while a `sentinel` exists → create a batch from all `bucket` pairs plus the sentinel pair. The batch is immediately moved into a dedicated staging directory named `<prefix>.__staged__<n>` and this folder path is advertised downstream.
- NGB arrives with no `sentinel` → enqueue as `pending_ngb`.

A TTL guard purges stale items (moves files to the exception area) if they linger too long in any transient state. Stale staging folders (leftover `<prefix>.__staged__<n>`) are also purged after TTL.

### Why staging?

- On a naming issue (invalid prefix, collision, or user-cancelled rename), the pipeline moves the advertised artefact to the rename bucket. By advertising the staging directory, the entire batch moves together, not just the last-arrived file.
- The pipeline automatically ignores internal staging markers when deriving the filename prefix, so downstream routing works as before.

Idempotency: If the sentinel NGB is observed again by the watcher (e.g., re-scan), preprocessing returns the same staging directory path without creating a new one.

## Filenames and numbering

- Prefix source: `Probenname` value from the CSV header metadata.
- Separator: `id_separator` from the active config (falls back to the project constant if no config context is active).
- Sequence: determined by scanning the target record directory for existing files with the same `<prefix>` and `<sep>NN` suffix; the next two-digit number is chosen. Example for a hyphen separator:
  - `Batch-42-01.csv` and `Batch-42-01.zip` (ZIP contains `Batch-42-01.ngb`)
  - `Batch-42-02.csv` and `Batch-42-02.zip`, etc.

Note: The plugin itself does not sanitize `Probenname`; downstream stages handle that. If the configured separator changes, numbering still aligns with existing files in the record directory.

## CSV parsing and encodings

- Recognizes both tab-separated and semicolon-separated headers.
- Reads a small prefix of the file and decodes using a cascade: `utf-8-sig`, `utf-8`, `cp1252`, then `latin-1` (fallback ignores undecodable bytes).
- Parses header lines until the numeric table begins. A line is considered part of the table when the first token looks like an axis header (e.g., `X(...)`) or a numeric value.
- Extracts metadata into a map with lower-cased keys; `probenname` is used as the prefix source.

## Probing and routing

`probe_file(path)`: Only CSV/TSV files are probed. The method scans the text prefix for Horiba markers (e.g., `horiba`, `partica`, `la-960`, `diameter`) and reduces confidence if dissolution-related terms are present. Returns a match with a bounded confidence or `unknown` if inconclusive.

`is_appendable(...)`: Always returns `True` to allow sequential numbering within the same record.

## Error handling and TTL purge

- A configurable TTL (`device_config.batch.ttl_seconds`, default 600s) controls staleness for:
  - Pending NGBs waiting for CSVs
  - Paired bucket entries waiting for sentinel
  - Sentinel CSVs waiting for the triggering NGB
- Stale files are moved to the exception folder via the platform’s `safe_move_to_exception` helper and the in-memory state is cleaned up.
- Extensive debug/info logs are emitted during state transitions and purges.

## Contract at a glance

Inputs
- `.ngb` native files and `.csv`/`.tsv` exported files in the same folder.

Outputs
- Destination record directory containing numbered CSVs and ZIPs, where each ZIP encapsulates a renamed `.ngb`.

Success criteria
- All pairs in a batch are moved/zipped with consistent `<prefix><sep>NN` basenames.
- Sequence numbers increment without collisions based on existing files in the record directory.

Error modes
- Missing counterpart just before finalization → raises with a clear message.
- Stale transient items → moved to exception area on purge.
- Stale staging folders → moved wholesale to exceptions on purge.

## Configuration

- `id_separator`: read from the active config; defaults to the project constant when config isn’t initialized.
- `batch.ttl_seconds`: optional; when present, overrides the default staleness window.

## Usage examples (happy paths)

1) Native→Exported order (NGB first, then CSV)
- Drop: `A.ngb` → queued as pending
- Drop: `B.csv` (with Probenname `Run-17`) → paired with `A.ngb` and added to the bucket
- Later, a sentinel CSV arrives and is followed by an NGB → all bucket pairs finalize using the sentinel’s `Probenname` prefix

2) Exported→Native order (CSV first, then NGB)
- Drop: `S.csv` (Probenname `Batch-42`) → remembered as sentinel
- Drop: `S.ngb` → triggers flush; processor creates `Batch-42.__staged__<n>` containing all CSV/NGB pairs in this batch and advertises the folder. The rename flow (if needed) moves this folder as one unit. On acceptance, processing reads from this folder and produces `Batch-42<sep>01.csv` and `Batch-42<sep>01.zip` (and so on).

## Troubleshooting

- Files not finalizing: ensure a sentinel CSV is followed by an NGB—finalization only occurs on this sequence.
- Unexpected filenames: remember that the prefix comes from the CSV’s `Probenname`, not the input filenames, and the separator is configurable.
- Stale purges: check `device_config.batch.ttl_seconds`. Purged files are moved to the exception directory; see logs for reasons.
- Encoding issues: the reader tries multiple encodings; if metadata is missing, verify the CSV header actually contains `Probenname`.

## Notes

- Zipping writes with `ZIP_DEFLATED` and removes the source `.ngb` after successful ZIP creation.
- The code is defensive around file disappearance between detection and processing; errors are logged and, where appropriate, exceptions are raised to surface actionable problems.
