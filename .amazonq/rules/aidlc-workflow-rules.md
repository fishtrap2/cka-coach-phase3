# AI-DLC Workflow Rules for cka-coach

Use the AI-Driven Development Life Cycle as a lightweight structure, not as bureaucracy.

## Phase 1: Inception

Before coding a feature, produce:
- problem statement
- user/student value
- ELS layers affected
- proposed architecture
- safety risks
- acceptance criteria
- test plan

## Phase 2: Construction

During implementation:
- make small commits
- preserve existing behavior
- update docs with code
- add validation scripts or manual test steps
- avoid destructive automation unless gated

## Phase 3: Operations

Before considering a feature complete:
- document how to run it
- document how to validate it
- document common failures
- document rollback/reset
- add learning moment if the feature teaches a concept
- update README or relevant docs

## Human control points

The human must approve:
- architecture changes
- destructive scripts
- dependency changes
- major UI redesigns
- Kubernetes install/removal behavior
- changes to ELS layer definitions