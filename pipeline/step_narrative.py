from __future__ import annotations

import json

from models.load_narrative_lora import get_narrative_model
from pipeline.orchestrator import DEFAULT_DECADES, LifeState, StepQualityError

NARRATIVE_SYSTEM = """
You are a memoir writer. Given a person's photo analysis and a life fork,
write a decade-by-decade alternate life as if the person is remembering it.
Write in first person. Be specific and sensory. Never be generic.
Each decade must contain one defining event, one relationship detail,
one physical sensation memory, and one regret or unexpected joy.
Return only valid JSON with decades as keys: "20s", "30s", "40s", "50s", "60s".
Each decade value must include narrative, key_event, emotion, location,
relationship, physical_memory, and aftertaste.
"""


async def step_narrative(state: LifeState):
    model, _tokenizer = get_narrative_model()
    analysis = state.photo_analysis or {
        "age_estimate": 28,
        "visible_context": ["portrait", "soft light"],
        "emotional_tone": "hopeful",
        "life_stage": "young_adult",
    }

    prompt = (
        f"Photo context: {json.dumps(analysis)}\n"
        f'Life fork: "{state.transcription or state.fork_text or "What if I had said yes?"}"\n'
        f"Language: {state.language_detected or 'en'}\n"
        f"Write this person's alternate life in the language detected above."
    )

    output = model.generate(
        system=NARRATIVE_SYSTEM,
        prompt=prompt,
        max_new_tokens=1800,
        temperature=0.85,
    )

    try:
        life_arc = json.loads(output)
    except json.JSONDecodeError as error:
        raise StepQualityError("narrative output not valid JSON") from error

    missing_decades = [decade for decade in DEFAULT_DECADES if decade not in life_arc]
    if missing_decades:
        raise StepQualityError(f"missing decades: {', '.join(missing_decades)}")

    required_fields = {"narrative", "key_event", "emotion", "location", "relationship", "physical_memory", "aftertaste"}
    for decade, details in life_arc.items():
        if required_fields - details.keys():
            raise StepQualityError(f"{decade} missing required narrative fields")

    state.life_title = _derive_life_title(state)
    state.life_summary = _derive_life_summary(life_arc)
    state.life_arc = {}
    for decade in DEFAULT_DECADES:
        state.life_arc[decade] = life_arc[decade]
        state.narrative_quality_score = round(len(state.life_arc) / len(DEFAULT_DECADES), 2)
        yield state


def _derive_life_title(state: LifeState) -> str:
    fork = (state.transcription or state.fork_text or "the unlived turn").strip().rstrip("?.!")
    cleaned = fork[:68] if len(fork) > 68 else fork
    if cleaned.lower().startswith("what if i had "):
        cleaned = cleaned[15:]
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return f"The Life Where I {cleaned}" if cleaned else "The Life Where I Turned"


def _derive_life_summary(life_arc: dict[str, dict[str, str]]) -> str:
    first = life_arc.get("20s", {})
    last = life_arc.get("60s", {})
    opening = first.get("location", "somewhere else")
    closing = last.get("aftertaste", "memory")
    return (
        f"A memoir of departure, reinvention, and the long echo of choice, "
        f"beginning in {opening} and ending in {closing}."
    )
