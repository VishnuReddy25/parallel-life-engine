---
title: Parallel Life Engine
emoji: "M"
colorFrom: amber
colorTo: red
sdk: gradio
pinned: false
license: apache-2.0
tags:
  - buildsmall
  - gradio
  - storytelling
  - multimodal
  - memoir
---

# Parallel Life Engine

Target Space: [build-small-hackathon/parallel-life-engine](https://huggingface.co/spaces/build-small-hackathon/parallel-life-engine)

Upload one portrait. Speak or type one sentence that begins with a fork in the road. Watch an unlived life rebuild itself into a cinematic scrapbook of decades, memories, portraits, and regrets.

## Hook

Parallel Life Engine is a machine for mourning the lives you never lived.

Instead of answering a prompt with generic advice or a one-shot story, it treats one alternate decision as the seed of a full memoir. The result is an artifact that feels closer to a found diary than a chatbot response.

## What the demo shows

- A Gradio interface instead of a raw API demo
- Typed or recorded fork input
- Progressive decade-by-decade reveal
- Portrait generation layered onto memoir text
- Exportable keepsake HTML
- Replayable saved runs from earlier generations
- Visible runtime diagnostics so viewers know whether the app is in mock/demo mode

## Why it fits Build Small

- The product is built around orchestration of small specialist steps, not one giant model
- The UX is intentionally compact: one image, one sentence, one artifact
- The output feels surprising and emotionally sticky, which is strong hackathon-demo material

## Space runtime target

This Space is designed to run as a Gradio Space in two modes:

- `PLE_MODEL_PROVIDER=mock` for fast local/demo verification
- `PLE_MODEL_PROVIDER=hf` for true off-grid Space inference on the attached GPU

In `hf` mode, the app loads the selected models inside the Space process and unloads them between stages. No inference API calls are required.

Recommended Space settings:

- SDK: `gradio`
- Hardware: `ZeroGPU` or a larger GPU tier depending on final model fit
- `PLE_MODEL_PROVIDER=hf`
- `PLE_DEMO_MODE=false`
- `PLE_TRACES_PROVIDER=local`
- `PLE_HF_SPACE_ID=build-small-hackathon/parallel-life-engine`
- optional `HF_TOKEN` secret for gated/private repos

The local web app also exposes simple operational endpoints for inspection:

- `GET /health`
- `GET /meta`
- `GET /providers`
- `GET /runs/<trace_id>`

## Local run

```powershell
py -m pip install -r requirements.txt
py scripts/verify.py
py -m uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
