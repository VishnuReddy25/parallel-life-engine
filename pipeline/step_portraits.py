from __future__ import annotations

from models.load_flux import get_flux
from pipeline.orchestrator import LifeState

PORTRAIT_TEMPLATE = """
Portrait photo of a {age}-year-old {life_stage} person.
Setting: {location}, {era}.
Mood: {emotion}. Style: candid documentary photograph.
Natural lighting. Film grain appropriate to {era}.
No text, no watermarks.
"""

DECADE_AGES = {"20s": 25, "30s": 35, "40s": 45, "50s": 55, "60s": 65}
DECADE_ERAS = {"20s": "2000s", "30s": "2010s", "40s": "2020s", "50s": "2030s", "60s": "2040s"}
FALLBACK_PORTRAIT_LIMIT = 3


async def step_portraits(state: LifeState):
    if not state.life_arc:
        yield state
        return

    flux = get_flux()
    analysis = state.photo_analysis or {"life_stage": "adult"}
    decades = list(state.life_arc.keys())
    portrait_targets = decades if len(decades) <= FALLBACK_PORTRAIT_LIMIT else decades[: len(decades)]

    for index, decade in enumerate(portrait_targets):
        data = state.life_arc[decade]
        age = DECADE_AGES.get(decade, 40)
        era = DECADE_ERAS.get(decade, "2020s")
        prompt = PORTRAIT_TEMPLATE.format(
            age=age,
            life_stage=analysis.get("life_stage", "adult"),
            location=data.get("location", "unknown city"),
            era=era,
            emotion=data.get("emotion", "contemplative"),
        )
        state.portrait_prompts[decade] = prompt

        try:
            state.portraits[decade] = flux.generate(
                prompt=prompt,
                reference_image=state.photo,
                reference_strength=0.55,
                num_inference_steps=28,
                guidance_scale=7.0,
            )
        except Exception as error:  # pragma: no cover - defensive path
            state.portrait_failures.append(f"{decade}: {error}")
            if len(decades) > FALLBACK_PORTRAIT_LIMIT and index >= FALLBACK_PORTRAIT_LIMIT - 1:
                break
        yield state
