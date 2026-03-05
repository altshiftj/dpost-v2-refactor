Stabilization-4 Cloud Launch Pack (V2 Runtime Hardening)

Run one cloud agent per lane using these prompt files:
- docs/ops/lane-prompts/stabilization-runtime-resilience-cloud.md
- docs/ops/lane-prompts/stabilization-ingestion-robustness-cloud.md
- docs/ops/lane-prompts/stabilization-observability-quality-cloud.md
- docs/ops/lane-prompts/stabilization-ci-reliability-cloud.md

Cloud guardrails:
- Each prompt includes branch bootstrap that works with or without `origin`.
- If `origin` is unavailable, agent continues in `NO_PUSH_MODE` and must output full diff.
- Do not provide tokens/secrets in prompts.

Coordinator expectation:
- Collect each lane output.
- If lane ran with `NO_PUSH_MODE`, apply patch locally on matching branch and push from local.
- Merge after lane validation passes.
