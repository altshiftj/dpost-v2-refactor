Three-Plugin 5-Lane Launch Pack

Use this pack after the V2 handshake closeout is accepted.

Lanes:
- `lane0-spec-lock`
- `laneA-sem-phenomxl2`
- `laneB-utm-zwick`
- `laneC-psa-horiba`
- `laneD-closeout`

Prompt file paths:
- `docs/ops/lane-prompts/three-plugin-lane0-spec-lock.md`
- `docs/ops/lane-prompts/three-plugin-laneA-sem-phenomxl2.md`
- `docs/ops/lane-prompts/three-plugin-laneB-utm-zwick.md`
- `docs/ops/lane-prompts/three-plugin-laneC-psa-horiba.md`
- `docs/ops/lane-prompts/three-plugin-laneD-closeout.md`

Coordination docs:
- `docs/planning/20260305-v2-three-plugin-parallel-lanes-rpc.md`
- `docs/checklists/20260305-v2-three-plugin-parallel-coordination-checklist.md`

Execution rules:
- run one lane per dedicated worktree or branch
- do not edit outside lane scope
- do not reopen shared runtime-wiring seams in plugin lanes
- merge `lane0` first and `laneD` last
