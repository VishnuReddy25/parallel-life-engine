from __future__ import annotations

from models.load_minicpm_o import get_minicpm_o
from pipeline.orchestrator import LifeState


async def step_asr(state: LifeState) -> LifeState:
    if state.fork_text:
        state.transcription = state.fork_text
        state.language_detected = "en"
        return state

    model = get_minicpm_o()
    result = model.transcribe(state.voice_audio or b"")
    state.transcription = str(result["text"])
    state.language_detected = str(result.get("language", "en"))
    if float(result.get("confidence", 1.0)) < 0.7:
        state.transcription = f"{state.transcription} (recovered from a noisy recording)"
    return state
