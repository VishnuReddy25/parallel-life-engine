# Artifact Index

This file is the quickest way to orient yourself in the current Parallel Life Engine repo.

## Core app

- Web entrypoint: [app.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/app.py)
- Frontend shell: [frontend/index.html](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/frontend/index.html)
- Frontend logic: [frontend/app.js](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/frontend/app.js)
- Pipeline state/orchestration: [pipeline/orchestrator.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/orchestrator.py)

## Runtime and verification

- Runtime config contract: [settings.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/settings.py)
- Env example: [.env.example](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/.env.example)
- Machine-readable repo summary: [project-manifest.json](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/project-manifest.json)
- Machine-readable schemas: [schemas](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/schemas)
- Operational JSON schemas: `health-response.schema.json`, `meta-response.schema.json`, `providers-response.schema.json`
- Example machine-readable outputs: [examples](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/examples)
- Smoke verifier: [scripts/verify.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/scripts/verify.py)
- Operational endpoints:
  - `GET /health`
  - `GET /meta`
  - `GET /runs/<trace_id>`

## Submission kit

- Space-facing pitch and metadata: [SPACE_README.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/SPACE_README.md)
- Demo talk track: [docs/demo-script.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/demo-script.md)
- Judge-facing summary: [docs/judge-brief.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/judge-brief.md)
- Final pre-submit checklist: [docs/submission-checklist.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/submission-checklist.md)
- Implementation handoff for real providers: [docs/integration-map.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/integration-map.md)
- Current repo claim audit: [docs/requirements-audit.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/requirements-audit.md)

## Saved outputs

- Run artifacts directory: [artifacts/runs](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/artifacts/runs)
- Each run contains:
  - `trace.json`
  - `keepsake.html`

## Current truth

- Supported runtime today:
  - `PLE_MODEL_PROVIDER=mock`
  - `PLE_DEMO_MODE=true`
  - `PLE_TRACES_PROVIDER=local`
- The repo already demonstrates:
  - typed and spoken fork intake
  - progressive narrative reveal
  - progressive portrait reveal
  - replayable saved runs
  - exportable keepsakes
  - visible runtime diagnostics
- The remaining external integration work is:
  - real Hugging Face-backed model providers
  - non-local trace upload/persistence
