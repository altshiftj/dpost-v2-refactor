# Eirich File Processor: Filename Routing via Upload Folder

## Problem Statement

Eirich exports are plain `.txt` files that sit alongside other device outputs. The previous plan used content fingerprinting to identify Eirich files, but that approach feels heavier than needed. We want a simpler, more explicit flow: users drop the raw Eirich file into an upload folder and the system routes it based on the filename.

This plan replaces the earlier content-based fingerprinting approach.

## Proposed Approach

- Users drop raw Eirich exports into the standard upload folder.
- Device selection is based on filename patterns, not content parsing.
- The file resolver (or `FileProcessManager`) picks the processor whose config declares a matching pattern.
- If no pattern matches, fall back to existing probe logic.
 - Once the Eirich processor is selected, it identifies the specific device variant
   (R01 vs EL1) from the filename prefix.
 - After device variant selection, prompt the user for initials, institute, and sample name.
 - Rename output to `RMX-{sample_name}` (Rotary Mixer abbreviation + sample name).

## Assumptions

- Eirich export filenames remain stable (examples: `Eirich_*`, `*_TrendFile_*`).
- A shared upload folder is acceptable unless we decide to split by device.

## Open Questions

- Do we want only Eirich-prefixed patterns, or do we also accept generic `*_TrendFile_*`?
- What is the expected behavior if multiple processors claim the same filename?
- Should we introduce a dedicated per-device upload folder instead of a shared one?
- How should we model multiple Eirich devices with near-identical file formats?
- Should the prompt happen before or after any preprocessing/record routing?
- How should we handle name collisions for `RMX-{sample_name}`?

## Multi-Device Options (R01 + EL1)

We currently have two Eirich devices with stable filename prefixes:

- `Eirich_R01_TrendFile_YYYYMMDD_HHMMSS`
- `Eirich_EL1_TrendFile_YYYYMMDD_HHMMSS`

This creates a clean routing signal for device selection. There are two viable approaches:

### Option A: Two device configs, one processor

- Keep a single `FileProcessorEirich`.
- Define two device configs (`rmx_eirich_r01`, `rmx_eirich_el1`) that:
  - Share the same processor class.
  - Provide distinct filename patterns (e.g., `Eirich_R01_*`, `Eirich_EL1_*`).
  - Carry per-device metadata (device name, record routing, storage target, etc.).

**Pros:** minimal code duplication, one implementation to maintain, easy to add more Eirich devices later.  
**Cons:** requires resolver to support multiple configs mapping to the same processor.

### Option B: Two processors (thin wrappers)

- Create two processors that subclass or wrap the shared Eirich logic.
- Each processor hardcodes its device identity and filename pattern.

**Pros:** simple resolver logic (one processor per device).  
**Cons:** code duplication or thin indirection; more moving parts for tests and config.

### Recommendation (plan-level)

Prefer Option A unless the resolver architecture cannot associate multiple device configs with a single processor. The filename prefix already encodes device identity, so config-only separation provides clean routing without multiplying code.

Decision:
- Implemented Option B (two processors) to align with per-device plugins.

## Proposed Flow (based on filename -> device -> rename)

1. Resolver selects the Eirich processor when filename contains `Eirich_*`.
2. Processor inspects the second prefix token to map to device variant:
   - `Eirich_R01_*` -> device variant `R01`
   - `Eirich_EL1_*` -> device variant `EL1`
3. Map device variant to record identifier prefix:
   - `EL1` -> `RMX_01`
   - `R01` -> `RMX_02`
4. Prompt user for:
   - initials
   - institute
   - sample name
5. Output filename: `RMX-{sample_name}`.
6. Continue with normal routing and record creation using the chosen device variant.

## Implementation Checklist

### 1. Define filename patterns in config

- [x] Add Eirich filename patterns to `rmx_eirich_el1/settings.py` and `rmx_eirich_r01/settings.py`.
- [x] Ensure pattern matching is case-insensitive.
- [x] Document accepted patterns for operators.
Notes:
- Accepted patterns: `Eirich_EL1_TrendFile_*`, `Eirich_R01_TrendFile_*`.
- Matching is case-insensitive via lowercasing before `fnmatch`.

### 2. Routing logic in resolver / `FileProcessManager`

- [x] Load filename patterns from each device config.
- [x] If a filename matches, route directly to that processor with high confidence.
- [x] If no match, fall back to existing probe logic.
- [x] If multiple matches occur, enforce a deterministic tie-breaker and log it.
Notes:
- Probing uses `device_config.files.filename_patterns` in each processor.
- DeviceResolver ties break on confidence then selector order, with debug logging.

### 3. Tests

- [x] Filename-only routing selects the Eirich processor.
- [x] Non-Eirich `.txt` files do not route to Eirich.
- [x] Collision behavior is deterministic and visible in logs.
Notes:
- Added probe + resolver coverage for EL1/R01 filename routing and non-matches.
- Added a confidence-tie resolver test and a debug log for tie-breaking.

### 4. Documentation

- [x] Update `decisionlog.md` after implementation.
Notes:
- Recorded the Eirich plugin split decision in `decisionlog.md`.
