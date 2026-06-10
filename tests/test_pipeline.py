import json

import pytest
from PIL import Image

from models.providers.hf_provider import get_provider_metadata
from pipeline.orchestrator import LifeState, StepQualityError, run_pipeline
from pipeline.step_asr import step_asr
from pipeline.step_export import step_export
from pipeline.step_narrative import step_narrative
from pipeline.step_portraits import step_portraits
from pipeline.step_structure import step_structure
from pipeline.step_vision import step_vision
from pipeline.trace_store import persist_run_artifacts
from runtime_validation import get_runtime_validation


@pytest.mark.asyncio
async def test_typed_fork_bypasses_asr():
    state = LifeState(fork_text="What if I had gone north?")
    updated = await step_asr(state)
    assert updated.transcription == "What if I had gone north?"
    assert updated.language_detected == "en"


@pytest.mark.asyncio
async def test_audio_fork_uses_mock_asr():
    state = LifeState(voice_audio=b"fake-audio")
    updated = await step_asr(state)
    assert "train line ended" in updated.transcription
    assert updated.language_detected == "en"


@pytest.mark.asyncio
async def test_narrative_generates_all_decades():
    state = LifeState(fork_text="What if I had gone north?", transcription="What if I had gone north?")
    snapshots = []
    async for partial in step_narrative(state):
        snapshots.append(partial)
    updated = snapshots[-1]
    assert list(updated.life_arc.keys()) == ["20s", "30s", "40s", "50s", "60s"]
    for decade in updated.life_arc.values():
        assert "relationship" in decade
        assert "aftertaste" in decade


@pytest.mark.asyncio
async def test_pipeline_happy_path_produces_export():
    photo = Image.new("RGB", (256, 256), "#c9b59f")
    state = LifeState(photo=photo, fork_text="What if I had moved to Tokyo at 22?")
    snapshots = []
    async for snapshot in run_pipeline(state):
        snapshots.append(snapshot)

    final_state = snapshots[-1]
    assert final_state.export_ready is True
    assert final_state.scrapbook_html
    assert len(final_state.portraits) >= 1
    assert final_state.timeline


@pytest.mark.asyncio
async def test_pipeline_streams_partial_decades_before_completion():
    photo = Image.new("RGB", (256, 256), "#c9b59f")
    state = LifeState(photo=photo, fork_text="What if I had moved to Tokyo at 22?")
    partial_counts = []
    async for snapshot in run_pipeline(state):
        if snapshot.life_arc:
            partial_counts.append(len(snapshot.life_arc))
    assert partial_counts[:5] == [1, 2, 3, 4, 5]
    assert 5 in partial_counts


@pytest.mark.asyncio
async def test_structure_requires_life_arc():
    with pytest.raises(StepQualityError):
        await step_structure(LifeState())


@pytest.mark.asyncio
async def test_export_embeds_pages():
    state = LifeState(
        life_arc={
            "20s": {
                "narrative": "I left home.",
                "key_event": "Left home",
                "emotion": "yearning",
                "location": "Osaka",
                "relationship": "my sister wrote back",
                "physical_memory": "rain in my shoes",
                "aftertaste": "wonder",
            }
        }
    )
    state.transcription = "What if I had left?"
    state.language_detected = "en"
    updated = await step_export(state)
    assert "\"20s\"" in updated.scrapbook_html
    assert "\"transcription\"" in updated.scrapbook_html


def test_persist_run_artifacts_writes_files(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.trace_store.RUNS_DIR", tmp_path)
    state = LifeState(
        life_title="The Life Where I Stayed",
        life_summary="A small life with a long echo.",
        transcription="What if I had stayed?",
        language_detected="en",
        life_arc={
            "20s": {
                "narrative": "I left home.",
                "key_event": "Left home",
                "emotion": "yearning",
                "location": "Osaka",
                "relationship": "my sister wrote back",
                "physical_memory": "rain in my shoes",
                "aftertaste": "wonder",
            }
        },
        scrapbook_html="<html>demo</html>",
        export_ready=True,
    )
    updated = persist_run_artifacts(state)
    assert updated.trace_id
    assert updated.trace_path
    assert updated.export_path


@pytest.mark.asyncio
async def test_portrait_failures_do_not_block_export(monkeypatch):
    async def fake_step_portraits(state):
        state.portrait_failures.append("20s: failed")
        return state

    state = LifeState(
        photo=Image.new("RGB", (128, 128), "#aaa"),
        fork_text="What if I had stayed?",
        transcription="What if I had stayed?",
    )
    snapshots = []
    async for partial in step_narrative(state):
        snapshots.append(partial)
    state = snapshots[-1]
    state = await step_structure(state)
    state = await fake_step_portraits(state)
    state = await step_export(state)
    assert state.export_ready is True
    assert state.portrait_failures


def test_hf_provider_metadata_exposes_selected_stack():
    metadata = get_provider_metadata()
    assert metadata["implemented"] is True
    assert metadata["provider_key"] == "hf"
    assert metadata["stack"]["vision"]
    assert metadata["stack"]["portraits"]


def test_runtime_validation_stays_ok_in_default_mock_mode():
    result = get_runtime_validation()
    assert result["selected_model_provider"] == "mock"
    assert result["ok"] is True
