# Eirich File Processor: Content-Based Fingerprinting

## Problem Statement

The Eirich mixer exports `.txt` files to USB sticks, which are then processed on PCs that also handle other devices outputting `.txt` files (e.g., DSV dissolver, connected to the Horiba PC). The current `probe_file` implementation returns a fixed confidence of 0.6 for *any* `.txt` file, which loses to content-based probes from other processors and causes misrouting.

## Solution Overview

Implement content-based fingerprinting that inspects file headers and filename patterns to reliably identify Eirich exports. This follows the established pattern used by `psa_horiba`, `rhe_kinexus`, and `dsv_horiba` processors.

---

## Implementation Checklist

### 1. Add `_read_text_prefix` helper method

- [x] Add static method to safely read first ~4KB of file
- [x] Handle encoding fallback chain: `utf-8-sig` → `utf-8` → `cp1252` → `latin-1`
- [x] Return decoded text snippet for content inspection

**Status:** `_read_text_prefix` now lives on `FileProcessorEirich` with the full encoding fallback chain and is covered by tests that assert truncation to the byte limit and proper decoding of CP1252 bytes (e.g., `°C`).

**Justification:** Eirich files may contain special characters (e.g., `°C`). A robust encoding fallback prevents probe failures on non-UTF8 files. Reading only 4KB keeps probing lightweight.

---

### 2. Define Eirich-specific positive markers

- [x] Add list of unique column header tokens:
  - `rotorrev` — Rotor revolution speed (1/min)
  - `rotorpower` — Rotor power consumption (W)
  - `mixingpanrev` — Mixing pan revolution (1/min)
  - `mixingpanpower` — Mixing pan power (W)
  - `rotorspeed` — Rotor tip speed (m/s)
  - `mixingpanspeed` — Pan circumferential speed (m/s)

**Status:** Defined `EIRICH_POSITIVE_MARKERS` as a frozenset containing the six highly specific column names found in Eirich exports. Tests verify the marker set contents and ensure all tokens are lowercase for case-insensitive matching.

**Justification:** These column names are highly specific to Eirich intensive mixers and do not appear in exports from other lab devices. Finding 2+ markers provides strong identification confidence.

---

### 3. Define negative markers for exclusion

- [ ] ~~Add list of tokens indicating other devices~~
  - ~~`dissolution`, `release`, `medium` — DSV Horiba dissolver~~
  - ~~`horiba`, `partica`, `la-960`, `diameter` — PSA Horiba~~
  - ~~`kinexus`, `rspace`, `viscosity` — Kinexus rheometer~~
  - ~~`zwick`, `tensile`, `strain` — Zwick UTM~~

**Status:** Decision made to drop negative marker heuristics entirely. Instead, we will design Eirich positives (header columns + filename patterns) strong enough that the resolver can simply pick the highest-confidence `MATCH`. This keeps probing localized inside each processor and avoids the complexity of synchronizing exclusion lists across devices.

**Justification (superseded):** Negative markers prevent false positives when a generic `.txt` file happens to contain some Eirich-like numeric columns. If a file contains dissolver-specific terms, it's clearly not an Eirich export.

---

### 4. Store markers in `DeviceConfig`

- [x] Extend `mix_eirich/settings.py` so the device's `DeviceConfig` carries a `markers` structure (positive tokens + filename patterns)
- [x] Update the processor to read markers from config instead of module-level constants

**Status:** Added `ContentMarkers` dataclass to `core/config/schema.py` with fields for positive markers, filename patterns, and scoring parameters. Updated `mix_eirich/settings.py` to populate markers in the config. Added tests verifying config structure and marker content.

**Justification:** Persisting markers in the config keeps all device-specific fingerprints in one place and mirrors how other selectors (extensions, native formats) are declared. It also makes future factory/resolver refactors easier because metadata lives with the config rather than scattered through processors.

---

### 5. Add filename prefix detection

- [x] Check if filename matches Eirich naming pattern: `Eirich_*` or `*_TrendFile_*`
- [x] Add bonus score (+1) when filename pattern matches

**Status:** Implemented `_matches_filename_pattern()` helper that uses `fnmatch` to check if the filename (case-insensitive) matches any configured pattern from `device_config.markers.filename_patterns`. Tests cover positive matches, non-matches, and case insensitivity.

**Justification:** Eirich exports use predictable naming like `Eirich_EL1_TrendFile_20250924_095653.txt`. This provides a secondary confidence signal that works even if header parsing fails. The bonus is additive rather than exclusive—content markers remain the primary identifier.

---

### 6. Implement scoring algorithm in `probe_file`

- [x] Calculate: `score = positive_hits + filename_bonus`
- [x] Return `FileProbeResult.unknown()` when `score <= 0`
- [x] Return `FileProbeResult.match(confidence=min(base + per_hit * score, max))` when `score > 0`

**Status:** Rewrote `probe_file()` to use content fingerprinting. Reads file prefix, counts positive marker hits in lowercase text, adds filename bonus, computes confidence using config-driven formula. Tests cover all scenarios: extension mismatch, unreadable files, no markers, filename-only match, full Eirich file, and partial markers.

**Justification:** The scoring formula matches existing processors (PSA Horiba, Kinexus). A score of 2+ yields confidence ≥0.85, which beats extension-only probes (0.6) and ties/beats most content probes.

---

### 7. Handle edge cases

- [x] Return `FileProbeResult.mismatch()` for non-`.txt` extensions
- [x] Return `FileProbeResult.unknown()` when file cannot be read (with exception message)
- [x] Ensure case-insensitive matching for all markers

**Status:** All edge cases are already implemented and tested as part of step 6. Extension check happens first in `probe_file()`, file read errors are caught with try/except and return `unknown` with the exception message, and marker matching uses `.lower()` on both the text content and stored markers (which are pre-normalized to lowercase).

**Justification:** Robust error handling prevents crashes on corrupted files. Case-insensitive matching handles variations in export software versions.

---

### 8. Add unit tests

- [x] Test: valid Eirich file → high confidence match (≥0.85)
- [x] Test: Eirich filename pattern alone → modest match (~0.70)
- [x] Test: DSV Horiba `.txt` file → unknown (no positive markers)
- [x] Test: unreadable file → unknown with error reason
- [x] Test: non-`.txt` extension → mismatch

**Status:** All required test scenarios are covered:
- `test_probe_file_full_eirich_file_high_confidence` - validates full file with 6 markers + filename → 0.95
- `test_probe_file_content_only_high_confidence` - validates 6 markers without filename → 0.95
- `test_probe_file_filename_only_gives_modest_confidence` - validates filename bonus only → 0.70
- `test_probe_file_partial_markers_moderate_confidence` - validates 2 markers → 0.85
- `test_probe_file_unknown_when_no_markers_found` - validates generic `.txt` → unknown
- `test_probe_file_unknown_when_file_unreadable` - validates missing file → unknown with error
- `test_probe_file_rejects_non_txt_extension` - validates `.csv` rejection → mismatch

**Justification:** Tests ensure the fingerprinting logic works correctly and doesn't regress when other processors are modified.

---

## Expected Confidence Scores

| Scenario | Positive Hits | Filename Bonus | Score | Confidence |
|----------|----------------|----------------|-------|------------|
| Full Eirich file | 6 | +1 | 7 | 0.95 |
| Eirich file (no filename match) | 6 | 0 | 6 | 0.95 |
| Filename only (empty content) | 0 | +1 | 1 | 0.70 |
| DSV Horiba `.txt` | 0 | 0 | 0 | unknown |
| Generic `.txt` | 0 | 0 | 0 | unknown |

---

## Files to Modify

- `src/ipat_watchdog/device_plugins/mix_eirich/file_processor.py` — Main implementation
- `tests/unit/test_eirich_file_processor.py` — Unit tests (create new)
