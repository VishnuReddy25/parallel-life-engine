# Integration Map

This document turns the remaining "future work" in Parallel Life Engine into concrete implementation seams based on the current repo.

## Goal

Replace the current demo-mode mock providers with real Hugging Face-backed integrations without changing the user-facing flow:

- one portrait
- one typed or spoken fork
- progressive scrapbook reveal
- replayable saved artifacts

## Current seam lines

### Runtime selection

- Runtime config: [settings.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/settings.py)
- Current mode:
  - `PLE_MODEL_PROVIDER=mock`
  - `PLE_DEMO_MODE=true`
  - `PLE_TRACES_PROVIDER=local`

The repo already expects provider switching through `SETTINGS`.

### Model loader swap points

- Vision loader: [models/load_minicpm_v.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/load_minicpm_v.py)
- ASR loader: [models/load_minicpm_o.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/load_minicpm_o.py)
- Narrative loader: [models/load_narrative_lora.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/load_narrative_lora.py)
- Structure loader: [models/load_nemotron_parse.py](C:/Users\vishn/OneDrive/Desktop/parallel-life-engine/models/load_nemotron_parse.py)
- Portrait loader: [models/load_flux.py](C:/Users\vishn/OneDrive/Desktop/parallel-life-engine/models/load_flux.py)
- Provider registry: [models/provider_registry.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/provider_registry.py)
- Mock provider implementation: [models/providers/mock_provider.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/providers/mock_provider.py)
- Placeholder Hugging Face provider module: [models/providers/hf_provider.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/models/providers/hf_provider.py)

Each file already exports a single getter. The safest integration path is:

1. Keep the exported function names unchanged.
2. Add a real provider branch keyed off `SETTINGS.model_provider`.
3. Preserve the same call signatures that the step modules already use.

## Required provider contracts

### Vision contract

Used by [pipeline/step_vision.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/step_vision.py)

Required behavior:

- Accept a portrait image
- Return valid JSON with:
  - `age_estimate`
  - `decade_of_photo`
  - `visible_context`
  - `emotional_tone`
  - `geographic_clues`
  - `life_stage`

### ASR contract

Used by [pipeline/step_asr.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/step_asr.py)

Required behavior:

- Accept raw audio bytes
- Return a dict containing:
  - `text`
  - `language`
  - optional `confidence`

### Narrative contract

Used by [pipeline/step_narrative.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/step_narrative.py)

Required behavior:

- Accept the existing prompt assembly
- Return valid JSON containing all five decades
- Each decade must include:
  - `narrative`
  - `key_event`
  - `emotion`
  - `location`
  - `relationship`
  - `physical_memory`
  - `aftertaste`

### Structure contract

Used by [pipeline/step_structure.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/step_structure.py)

Required behavior:

- Accept flattened life-arc text
- Return a dict containing `timeline`

### Portrait contract

Used by [pipeline/step_portraits.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/step_portraits.py)

Required behavior:

- Accept the existing prompt string
- Optionally accept a reference image
- Return a PIL image per decade

## Trace persistence swap point

- Current implementation: [pipeline/trace_store.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/trace_store.py)
- Trace provider registry: [pipeline/trace_provider_registry.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/trace_provider_registry.py)
- Local trace provider: [pipeline/trace_providers/local_provider.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/trace_providers/local_provider.py)
- Placeholder hosted trace provider: [pipeline/trace_providers/hosted_provider.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/pipeline/trace_providers/hosted_provider.py)
- Current mode: local filesystem under `artifacts/runs/`

Real integration path:

1. Keep local persistence as the default fallback.
2. Add a hosted branch behind `PLE_TRACES_PROVIDER`.
3. Preserve the current state fields:
   - `trace_id`
   - `trace_path`
   - `export_path`
4. If hosted traces do not map naturally to paths, return stable URL-like strings in those fields.

## Deployment seam

- App entrypoint: [app.py](C:/Users/vishn/OneDrive/Desktop/parallel-life-engine/app.py)
- Operational endpoints:
  - `GET /health`
  - `GET /meta`
  - `GET /runs/<trace_id>`

Deployment work should preserve those routes so the submission kit and verifier remain valid.

## Safe order of implementation

1. Replace narrative provider first.
   This changes the perceived product quality the most.
2. Replace trace persistence second.
   This upgrades the demo story and replay value.
3. Replace ASR and vision providers.
4. Replace portrait provider last if GPU/runtime constraints are hardest there.

## Non-negotiables to preserve

- `LifeState` remains the inter-step contract
- `/run` remains the only generation endpoint
- progressive reveal stays intact
- exportable keepsake HTML remains available
- replay shelf still works after persistence changes
