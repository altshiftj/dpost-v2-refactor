# Hioki file processor helpers refactor checklist

Target: split `FileProcessorHioki.device_specific_processing` into smaller helpers without changing behavior.

- [x] Extract helpers for measurement, CC, and aggregate handling.
  - Justification: improves readability and isolates file movement logic.
  - Resolved: split into `_process_measurement_csv`, `_process_cc_csv`, and `_process_aggregate_csv`.
- [x] Keep the public behavior identical (paths, force uploads, copy vs move).
  - Justification: refactor only, no user-visible changes.
  - Resolved: maintained move/copy semantics and force paths in the helper methods.
- [x] Run existing Hioki unit tests that cover processing behavior.
  - Justification: safety check for refactor.
  - Resolved: `python -m pytest tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_processing_moves_measurement_and_forces_cc_aggregate tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_preprocessing_normalizes_measurement_name tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py::test_measurement_processed_even_when_aggregate_exists`.
