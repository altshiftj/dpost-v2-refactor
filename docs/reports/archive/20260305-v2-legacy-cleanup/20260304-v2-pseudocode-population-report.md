# Report: V2 Pseudocode Population Coverage

## Date
- 2026-03-04

## Scope
- Completed population of all non-README specs under `docs/pseudocode/**`.
- No edits made under `src/` or `tests/`.

## Validation Checks Run
- `rg "TBD" docs/pseudocode`
- `rg "origin|source|v1" docs/pseudocode -n`
- required section presence audit (`Intent`, `Inputs`, `Outputs`, `Invariants`, `Failure Modes`, `Pseudocode`, `Tests To Implement`)
- `origin_v1_files` frontmatter presence audit (all non-README pseudocode specs)
- `id` frontmatter path alignment audit against pseudocode file paths
- mapping spot-check against `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md` for:
  - `__main__`
  - runtime files
  - contracts files
  - plugin target paths (`plugins/host.py`, `plugins/discovery.py`, `plugins/catalog.py`, plus `<device>/<pc>` template targets)

## Parity-Risk Assessment
- Overall pseudocode completeness risk: low.
- Residual risk: medium in plugin and sync adapters due high variability of concrete implementations despite complete contract/template guidance.
- Mitigation before implementation:
  - prioritize contract conformance tests first in plugin and sync lanes
  - use typed failure normalization tests across ingestion + runtime services
  - keep lane boundaries strict (domain pure, side effects in infrastructure only)

## Final Status Matrix (`pending | done`)
```text
done | pseudocode/__main__.md
done | pseudocode/application/contracts/context.md
done | pseudocode/application/contracts/events.md
done | pseudocode/application/contracts/plugin_contracts.md
done | pseudocode/application/contracts/ports.md
done | pseudocode/application/ingestion/engine.md
done | pseudocode/application/ingestion/models/candidate.md
done | pseudocode/application/ingestion/policies/error_handling.md
done | pseudocode/application/ingestion/policies/failure_emitter.md
done | pseudocode/application/ingestion/policies/failure_outcome.md
done | pseudocode/application/ingestion/policies/force_path.md
done | pseudocode/application/ingestion/policies/immediate_sync_error_emitter.md
done | pseudocode/application/ingestion/policies/modified_event_gate.md
done | pseudocode/application/ingestion/policies/retry_planner.md
done | pseudocode/application/ingestion/processor_factory.md
done | pseudocode/application/ingestion/runtime_services.md
done | pseudocode/application/ingestion/stages/persist.md
done | pseudocode/application/ingestion/stages/pipeline.md
done | pseudocode/application/ingestion/stages/post_persist.md
done | pseudocode/application/ingestion/stages/resolve.md
done | pseudocode/application/ingestion/stages/route.md
done | pseudocode/application/ingestion/stages/stabilize.md
done | pseudocode/application/records/service.md
done | pseudocode/application/runtime/dpost_app.md
done | pseudocode/application/session/session_manager.md
done | pseudocode/application/startup/bootstrap.md
done | pseudocode/application/startup/context.md
done | pseudocode/application/startup/settings_schema.md
done | pseudocode/application/startup/settings_service.md
done | pseudocode/application/startup/settings.md
done | pseudocode/domain/naming/identifiers.md
done | pseudocode/domain/naming/policy.md
done | pseudocode/domain/naming/prefix_policy.md
done | pseudocode/domain/processing/batch_models.md
done | pseudocode/domain/processing/models.md
done | pseudocode/domain/processing/staging.md
done | pseudocode/domain/processing/text.md
done | pseudocode/domain/records/local_record.md
done | pseudocode/domain/routing/rules.md
done | pseudocode/infrastructure/observability/logging.md
done | pseudocode/infrastructure/observability/metrics.md
done | pseudocode/infrastructure/observability/tracing.md
done | pseudocode/infrastructure/runtime/ui/adapters.md
done | pseudocode/infrastructure/runtime/ui/desktop.md
done | pseudocode/infrastructure/runtime/ui/dialogs.md
done | pseudocode/infrastructure/runtime/ui/factory.md
done | pseudocode/infrastructure/runtime/ui/headless.md
done | pseudocode/infrastructure/runtime/ui/tkinter.md
done | pseudocode/infrastructure/storage/file_ops.md
done | pseudocode/infrastructure/storage/record_store.md
done | pseudocode/infrastructure/storage/staging_dirs.md
done | pseudocode/infrastructure/sync/kadi.md
done | pseudocode/infrastructure/sync/noop.md
done | pseudocode/plugins/catalog.md
done | pseudocode/plugins/contracts.md
done | pseudocode/plugins/devices/_device_template/plugin.md
done | pseudocode/plugins/devices/_device_template/processor.md
done | pseudocode/plugins/devices/_device_template/settings.md
done | pseudocode/plugins/discovery.md
done | pseudocode/plugins/host.md
done | pseudocode/plugins/pcs/_pc_template/plugin.md
done | pseudocode/plugins/pcs/_pc_template/settings.md
done | pseudocode/plugins/profile_selection.md
done | pseudocode/runtime/composition.md
done | pseudocode/runtime/startup_dependencies.md
```

## Remaining Gaps
- None in pseudocode population scope.
