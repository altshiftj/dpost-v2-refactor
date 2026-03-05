# Checklist: V2 Three-Plugin Parity Matrix

## Section: sem_phenomxl2
- Why this matters: SEM is the cleanest plugin surface and establishes the expected V2 processor pattern for native-image and ELID handling.

### Accepted Behaviors
- [x] `SEM001`: `.elid` directories remain valid SEM inputs alongside native image extensions.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/sem_phenomxl2/file_processor.py`
    - `src/ipat_watchdog/device_plugins/sem_phenomxl2/settings.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py::test_sem001_can_process_elid_directories`
- [x] `SEM002`: native image processing strips one trailing digit from the basename and emits datatype `img`.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/sem_phenomxl2/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py::test_sem002_process_native_image_normalizes_trailing_digit_and_sets_img_datatype`
- [x] `SEM003`: ELID directory processing yields datatype `elid` and carries the ZIP plus `.odt` and `.elid` descriptor artifacts together.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/sem_phenomxl2/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py::test_sem003_process_elid_directory_emits_zip_and_descriptor_artifacts`

### Deferred Behaviors
- [ ] Descriptor dedupe against pre-existing target names is deferred from lane0 encoding because current V2 processor tests do not have record-directory-aware allocation hooks yet.
- [ ] Legacy `is_appendable(...)` behavior is deferred from lane0 encoding because there is no direct V2 processor contract equivalent yet.

### Completion Notes
- How it was done:
  - Source and legacy-reference tests agree on the trailing-digit rule and ELID descriptor flow.
  - Lane0 only encoded behaviors that can be asserted through the current V2 processor surface.

---

## Section: utm_zwick
- Why this matters: UTM is the first staged multi-file processor and exposes whether V2 can express stateful series handling without legacy runtime fallback.

### Accepted Behaviors
- [x] `UTM001`: a matching `.zs2` followed by `.xlsx` finalizes as datatype `xlsx` and carries both raw and results artifacts.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/utm_zwick/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py::test_utm001_process_matching_xlsx_trigger_emits_raw_and_results_artifacts`
- [x] `UTM002`: orphan `.xlsx` input does not finalize a series without a matching `.zs2`.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/utm_zwick/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py::test_utm002_process_rejects_orphan_xlsx_without_matching_zs2`
- [x] `UTM003`: series pairing is exact-stem and case-sensitive.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/utm_zwick/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py::test_utm003_process_requires_exact_stem_match_for_series_pairing`

### Deferred Behaviors
- [ ] TTL/session-end flush of raw-only `.zs2` series is deferred from lane0 test encoding because the current V2 transform seam does not yet expose a first-class deferred/flush trigger.
- [ ] Unique target-path allocation and overwrite protection are deferred from lane0 encoding because current V2 processor tests do not receive routed record-directory state.
- [ ] Legacy `probe_file(...)` confidence behavior is deferred from lane0 encoding because current V2 selection is extension-driven and does not yet expose a probe contract.

### Completion Notes
- How it was done:
  - The legacy reference tests were treated as secondary evidence for stem pairing and orphan XLSX rejection.
  - Real-world filewatch traces in `src/ipat_watchdog/device_plugins/utm_zwick/docs/` confirmed the staged `.zs2` then `.xlsx` ordering.

---

## Section: psa_horiba
- Why this matters: PSA carries the most staging logic and is the strongest check that V2 can preserve bucketed flush behavior without leaking legacy runtime structure back in.

### Accepted Behaviors
- [x] `PSA001`: `.tsv` exported files are valid PSA inputs alongside `.csv` and `.ngb`.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py::test_psa001_can_process_tsv_exports_in_addition_to_csv_and_ngb`
- [x] `PSA002`: bucketed pairs plus a sentinel CSV->NGB flush use the sentinel `Probenname` prefix and emit numbered `.csv` and `.zip` artifacts.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`
    - `src/ipat_watchdog/device_plugins/psa_horiba/README.md`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py::test_psa002_process_sentinel_sequence_emits_numbered_csv_and_zip_artifacts`
- [x] `PSA003`: sentinel CSV alone does not finalize the batch.
  - Legacy source:
    - `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`
  - Legacy reference tests:
    - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/test_file_processor.py`
  - V2 red test:
    - `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py::test_psa003_process_requires_complete_sentinel_sequence_before_finalize`

### Deferred Behaviors
- [ ] TTL purge of pending NGBs, queued pairs, sentinel CSVs, and stale staging folders is deferred from lane0 test encoding because the current V2 processor seam does not yet provide explicit exception-bucket hooks.
- [ ] Reconstructing staged batches after in-memory state loss is deferred from lane0 test encoding because current V2 processor tests do not yet have a stable staged-folder contract.
- [ ] Rename-cancel moving the entire staged folder as one unit is deferred from lane0 test encoding because it depends on manual-bucket/rename-flow services outside the current V2 processor contract.
- [ ] Sequence allocation against pre-existing record-directory contents is deferred from lane0 encoding because current V2 processor tests do not receive routed target-directory state.

### Completion Notes
- How it was done:
  - The processor source, plugin README, and the additional purge/reconstruct legacy tests all point to the same batch model.
  - Lane0 encoded only the core sentinel-flush semantics that can be expressed without extending the shared runtime seam yet.
