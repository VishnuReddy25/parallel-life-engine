from __future__ import annotations

from models.load_nemotron_parse import get_nemotron_parse
from pipeline.orchestrator import LifeState, StepQualityError


async def step_structure(state: LifeState) -> LifeState:
    if not state.life_arc:
        raise StepQualityError("structure step requires life arc")

    parser = get_nemotron_parse()
    full_text = "\n\n".join(
        f"[{decade}] {data['narrative']}"
        for decade, data in state.life_arc.items()
    )
    result = parser.extract(text=full_text, schema={"timeline": []})
    timeline = result.get("timeline", [])
    if not timeline:
        raise StepQualityError("timeline extraction returned empty output")
    state.timeline = timeline
    return state
