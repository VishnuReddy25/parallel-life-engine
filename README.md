# Parallel Life Engine

Parallel Life Engine is a Build Small hackathon concept turned into a working repo scaffold: upload one portrait, give one life-fork sentence, and generate a decade-by-decade alternate-life scrapbook with memoir text, timeline traces, portraits, and a standalone keepsake export.

## What is implemented

- A sequential agentic pipeline with retry-aware step orchestration in [pipeline/orchestrator.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/orchestrator.py)
- Step modules for vision, ASR, memoir generation, structure extraction, portraits, and export
- A Gradio Blocks interface in [app.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/app.py)
- A scrapbook export template in [frontend](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/frontend)
- A Gradio Space-style entrypoint in [app.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/app.py) with a custom themed Blocks interface
- Async tests in [tests/test_pipeline.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/tests/test_pipeline.py)
- A dependency-light smoke verifier in [scripts/verify.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/scripts/verify.py)

## Current architecture

- `LifeState` is the only inter-step contract.
- Structured-output steps use retry semantics through `StepQualityError`.
- The current model loaders are mock adapters that preserve the intended interfaces, so real Hugging Face integrations can be swapped in without changing the step contracts.
- Export builds a self-contained scrapbook HTML artifact by embedding the generated payload directly into the frontend template.
- Completed runs are persisted under `artifacts/runs/<trace_id>/` with both `trace.json` and `keepsake.html`.
- The homepage can surface a replay shelf of recent saved runs, and `/runs/<trace_id>` serves the saved keepsake directly when the web app is running.

## Runtime modes

The repo now has an explicit runtime contract in [settings.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/settings.py):

- `PLE_MODEL_PROVIDER=mock`
  This is the current supported mode and powers the demo scaffold.
- `PLE_DEMO_MODE=true`
  Keeps the repo in showcase mode with mock-friendly behavior.
- `PLE_TRACES_PROVIDER=local`
  Persists artifacts under `artifacts/runs/`.

The `hf` model provider is now wired for local Hugging Face Space execution that defaults to:

- `openbmb/MiniCPM-V-4_6` for photo understanding
- `nvidia/parakeet-tdt-0.6b-v2` for ASR
- `openbmb/MiniCPM5-1B` for memoir generation
- `nvidia/Nemotron-Parse` for timeline extraction
- `black-forest-labs/FLUX.2-KONtext-klein` for portraits

In `hf` mode, models are loaded inside the app process and run on the Space GPU. The loader is stage-oriented and unloads models between major steps to fit a single-GPU hackathon deployment.

Non-local trace persistence is still an explicit future seam.

## Local setup

Install the declared dependencies:

```powershell
py -m pip install -r requirements.txt
```

Optional environment configuration:

```powershell
Copy-Item .env.example .env
```

To switch from the local showcase stack to Space-local GPU models:

```powershell
$env:PLE_MODEL_PROVIDER="hf"
$env:PLE_DEMO_MODE="false"
```

Public models can work without `HF_TOKEN`, but keep it set in Spaces for gated/private repos or higher reliability. Each model id and runtime flag can be overridden with the `PLE_HF_*` variables in [.env.example](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/.env.example).

For the current deployment target, set `PLE_HF_SPACE_ID=build-small-hackathon/parallel-life-engine`.

Provider inspection:

```powershell
py scripts/inspect_provider_manifest.py
```

Runtime validation:

```powershell
py scripts/validate_runtime.py
```

Example payload export:

```powershell
py scripts/export_examples.py
```

Run the lightweight verifier:

```powershell
py scripts/verify.py
```

Generated demo traces and exports will appear in `artifacts/runs/`.

Start the local app once dependencies are installed:

```powershell
py -m uvicorn app:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Operational endpoints:

- `GET /health`
- `GET /meta`
- `GET /providers`
- `GET /runs/<trace_id>`

## Next hackathon-facing upgrades

- Validate the exact local loader recipe for each chosen Hub model repo on the target Space GPU
- Swap local trace persistence for Hugging Face dataset-backed trace uploads

## Submission kit

- Repo-wide handoff index: [docs/artifact-index.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/artifact-index.md)
- Real-provider implementation map: [docs/integration-map.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/integration-map.md)
- Machine-readable project summary: [project-manifest.json](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/project-manifest.json)
- Machine-readable schemas: [schemas](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/schemas)
- Operational response schemas: `health-response.schema.json`, `meta-response.schema.json`, `providers-response.schema.json`
- Claim-to-evidence audit: [docs/requirements-audit.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/requirements-audit.md)
- Space-facing metadata and pitch: [SPACE_README.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/SPACE_README.md)
- Live demo talk track: [docs/demo-script.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/demo-script.md)
- Judge-facing positioning: [docs/judge-brief.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/judge-brief.md)
- Final pre-submit pass: [docs/submission-checklist.md](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/docs/submission-checklist.md)
