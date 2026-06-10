from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Optional

from PIL import Image

MAX_RETRIES = 2
DEFAULT_DECADES = ["20s", "30s", "40s", "50s", "60s"]


class StepQualityError(Exception):
    """Raised when a step completes but does not meet quality requirements."""


@dataclass
class LifeState:
    photo: Optional[Image.Image] = None
    voice_audio: Optional[bytes] = None
    fork_text: Optional[str] = None

    photo_analysis: Optional[dict[str, Any]] = None
    analysis_confidence: float = 0.0

    transcription: Optional[str] = None
    language_detected: Optional[str] = None

    life_arc: Optional[dict[str, dict[str, str]]] = None
    narrative_quality_score: float = 0.0

    timeline: Optional[list[dict[str, Any]]] = None

    portraits: dict[str, Image.Image] = field(default_factory=dict)
    portrait_prompts: dict[str, str] = field(default_factory=dict)
    portrait_failures: list[str] = field(default_factory=list)

    life_title: Optional[str] = None
    life_summary: Optional[str] = None
    trace_id: Optional[str] = None
    trace_path: Optional[str] = None
    export_path: Optional[str] = None
    scrapbook_html: Optional[str] = None
    export_ready: bool = False

    retry_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    yield_log: list[str] = field(default_factory=list)
    decades: list[str] = field(default_factory=lambda: list(DEFAULT_DECADES))


StepFn = Callable[[LifeState], Any]
ConditionFn = Callable[[LifeState], bool]


async def run_pipeline(state: LifeState) -> AsyncGenerator[LifeState, None]:
    from pipeline.step_asr import step_asr
    from pipeline.step_export import step_export
    from pipeline.step_narrative import step_narrative
    from pipeline.step_portraits import step_portraits
    from pipeline.step_structure import step_structure
    from pipeline.step_vision import step_vision

    steps: list[tuple[str, StepFn, ConditionFn]] = [
        ("vision", step_vision, requires_photo),
        ("asr", step_asr, requires_audio_or_text),
        ("narrative", step_narrative, always),
        ("structure", step_structure, always),
        ("portraits", step_portraits, always),
        ("export", step_export, always),
    ]

    for name, fn, condition in steps:
        if not condition(state):
            state.yield_log.append(f"skip:{name}")
            yield state
            continue

        state.retry_counts[name] = 0

        while state.retry_counts[name] <= MAX_RETRIES:
            try:
                state.yield_log.append(f"start:{name}")
                yield state

                maybe_state = fn(state)
                if hasattr(maybe_state, "__aiter__"):
                    last_state = state
                    async for partial_state in _iterate_step_stream(name, maybe_state):
                        last_state = partial_state
                        yield partial_state
                    state = last_state
                else:
                    state = await maybe_state if asyncio.iscoroutine(maybe_state) else maybe_state

                state.yield_log.append(f"done:{name}")
                yield state
                break
            except StepQualityError as error:
                state.retry_counts[name] += 1
                state.yield_log.append(f"retry:{name}:{error}")
                yield state
                if state.retry_counts[name] > MAX_RETRIES:
                    state.errors.append(f"{name} failed after retries: {error}")
                    yield state
                    break
            except Exception as error:  # pragma: no cover - defensive path
                state.errors.append(f"{name} error: {error}")
                state.yield_log.append(f"error:{name}")
                yield state
                break


def requires_photo(state: LifeState) -> bool:
    return state.photo is not None


def requires_audio_or_text(state: LifeState) -> bool:
    return state.voice_audio is not None or bool(state.fork_text)


def always(_: LifeState) -> bool:
    return True


async def _iterate_step_stream(name: str, stream: AsyncIterator[LifeState]) -> AsyncGenerator[LifeState, None]:
    async for partial_state in stream:
        partial_state.yield_log.append(f"stream:{name}")
        yield partial_state
