from __future__ import annotations

import json

from models.load_minicpm_v import get_minicpm_v
from pipeline.orchestrator import LifeState, StepQualityError

VISION_PROMPT = """
Analyse this photo carefully and return a JSON object with these exact keys:
- age_estimate: estimated age of the main subject (integer)
- decade_of_photo: estimated decade the photo was taken (e.g. "1980s")
- visible_context: list of 5 specific visible details (objects, clothing, setting)
- emotional_tone: one word describing the dominant emotion visible
- geographic_clues: any hints about location or culture
- life_stage: one of [child, teenager, young_adult, adult, elder]

Return only valid JSON. No preamble.
"""


async def step_vision(state: LifeState) -> LifeState:
    model, tokenizer = get_minicpm_v()
    response = model.chat(
        image=state.photo,
        msgs=[{"role": "user", "content": VISION_PROMPT}],
        tokenizer=tokenizer,
    )

    try:
        analysis = json.loads(response)
    except json.JSONDecodeError as error:
        raise StepQualityError("vision output not valid JSON") from error

    if not analysis.get("age_estimate") or not analysis.get("visible_context"):
        raise StepQualityError("vision output missing required fields")

    state.photo_analysis = analysis
    state.analysis_confidence = 0.9
    return state
