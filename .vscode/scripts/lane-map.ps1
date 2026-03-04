Set-StrictMode -Version Latest

function Get-LaneMap {
    return [ordered]@{
        "contracts-interfaces" = @{
            Branch = "rewrite/v2-lane-contracts-interfaces"
            Prompt = "docs/ops/lane-prompts/contracts-interfaces.md"
        }
        "startup-bootstrap" = @{
            Branch = "rewrite/v2-lane-startup-bootstrap"
            Prompt = "docs/ops/lane-prompts/startup-bootstrap.md"
        }
        "domain-core-models" = @{
            Branch = "rewrite/v2-lane-domain-core-models"
            Prompt = "docs/ops/lane-prompts/domain-core-models.md"
        }
        "ingestion-pipeline" = @{
            Branch = "rewrite/v2-lane-ingestion-pipeline"
            Prompt = "docs/ops/lane-prompts/ingestion-pipeline.md"
        }
        "infrastructure-adapters" = @{
            Branch = "rewrite/v2-lane-infrastructure-adapters"
            Prompt = "docs/ops/lane-prompts/infrastructure-adapters.md"
        }
        "plugins-device-system" = @{
            Branch = "rewrite/v2-lane-plugins-device-system"
            Prompt = "docs/ops/lane-prompts/plugins-device-system.md"
        }
        "runtime-composition" = @{
            Branch = "rewrite/v2-lane-runtime-composition"
            Prompt = "docs/ops/lane-prompts/runtime-composition.md"
        }
        "docs-pseudocode-traceability" = @{
            Branch = "rewrite/v2-lane-docs-pseudocode-traceability"
            Prompt = "docs/ops/lane-prompts/docs-pseudocode-traceability.md"
        }
        "tests-v2-harness" = @{
            Branch = "rewrite/v2-lane-tests-v2-harness"
            Prompt = "docs/ops/lane-prompts/tests-v2-harness.md"
        }
        "ci-v2-gates" = @{
            Branch = "rewrite/v2-lane-ci-v2-gates"
            Prompt = "docs/ops/lane-prompts/ci-v2-gates.md"
        }
    }
}
