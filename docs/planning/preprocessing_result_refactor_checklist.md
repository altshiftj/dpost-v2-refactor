# PreprocessingResult refactor checklist

Target: reduce repetition and clarify the preprocessing contract across processors.

- [x] Add helper factories on `PreprocessingResult` (e.g., `with_prefix`, `with_extension`) to standardize usage.
  - Justification: avoid ad hoc construction and make intent explicit.
  - Resolved: Added helpers in `PreprocessingResult`.
- [x] Apply the helpers in processors (Hioki, SEM, PSA, Kinexus, DSV, UTM, Eirich) to simplify their preprocessing implementations.
  - Justification: consistent style and less boilerplate.
  - Resolved: Hioki + SEM use `with_prefix`; PSA/Kinexus type hints aligned to PreprocessingResult; DSV/UTM/Eirich already use `passthrough`.
- [x] Optional: add a short doc snippet (README/CONTRIBUTING) describing the preprocessing/processing contract.
  - Justification: reduce future drift when adding processors.
  - Resolved: Added to `DEVELOPER_README.md`.
