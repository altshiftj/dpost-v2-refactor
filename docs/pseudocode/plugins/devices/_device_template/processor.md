---
id: plugins/devices/_device_template/processor.py
origin_v1_files:
  - src/dpost/device_plugins/dsv_horiba/file_processor.py
  - src/dpost/device_plugins/psa_horiba/file_processor.py
  - src/dpost/device_plugins/rmx_eirich_r01/file_processor.py
  - src/dpost/device_plugins/extr_haake/file_processor.py
  - src/dpost/device_plugins/utm_zwick/file_processor.py
  - src/dpost/device_plugins/test_device/file_processor.py
  - src/dpost/device_plugins/sem_phenomxl2/file_processor.py
  - src/dpost/device_plugins/erm_hioki/file_processor.py
  - src/dpost/device_plugins/rhe_kinexus/file_processor.py
  - src/dpost/device_plugins/rmx_eirich_el1/file_processor.py
lane: Plugin-Device
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Device-specific parsing, preprocessing, and candidate derivation logic.

## Origin Gist
- Source mapping: template derived from 10 device-plugin origin files.
- Legacy gist: Keeps device processing logic under consistent `processor.py` naming across mapped device families. Template coverage extends to all mapped variants listed in `origin_v1_files`.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Device-specific parsing, preprocessing, and candidate derivation logic.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Raw source artifact content and metadata references.
- Device plugin settings and processing context.
- Candidate metadata seed from resolve stage.
- Optional normalization helpers from domain processing modules.

## Outputs
- Required processor entry points:
  - `prepare(raw_input)` for format-specific preprocessing.
  - `process(prepared_input, context)` for candidate derivation/result production.
- Typed processor result model containing parsed payload, derived tokens, and warnings.
- Typed processor errors for unsupported formats/parse failures/validation failures.

## Invariants
- Processor behavior is deterministic for identical input + settings.
- Processor does not perform infrastructure side effects directly.
- `prepare` output type is valid input for `process`.
- Required `prepare` and `process` entry points are always present.

## Failure Modes
- Unsupported artifact format raises `DeviceProcessorFormatError`.
- Parse/normalization failure raises `DeviceProcessorParseError`.
- Missing required fields in parsed content raises `DeviceProcessorValidationError`.
- Unexpected runtime exception is wrapped as `DeviceProcessorUnexpectedError`.

## Pseudocode
1. Implement `prepare(raw_input)` to decode/normalize input into intermediate structured data.
2. Validate intermediate structure against device-specific schema expectations.
3. Implement `process(prepared_input, context)` to derive candidate payload and processing metadata.
4. Normalize derived values via domain processing/naming helpers.
5. Build typed processor result with warnings and deterministic field ordering.
6. Map parse/validation/runtime issues to typed processor errors.

## Tests To Implement
- unit: deterministic prepare/process outputs, unsupported format rejection, and required-field validation.
- integration: ingestion resolve/persist flow runs a concrete device processor from this template and consumes its typed result in downstream stages.



