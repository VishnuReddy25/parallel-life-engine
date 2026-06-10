import pytest

from models.providers import hf_provider
from pipeline.trace_providers import hosted_provider


def test_hf_provider_metadata_exposes_missing_env():
    metadata = hf_provider.get_provider_metadata()
    assert metadata["implemented"] is True
    assert metadata["mode"] == "local_space_gpu"
    assert metadata["runtime"]["offload_between_steps"] in {True, False}
    assert "missing_env" in metadata


def test_hf_provider_getters_return_local_adapters():
    vision, _ = hf_provider.get_minicpm_v()
    asr = hf_provider.get_minicpm_o()
    narrative, _ = hf_provider.get_narrative_model()
    structure = hf_provider.get_nemotron_parse()
    portrait = hf_provider.get_flux()
    assert hasattr(vision, "chat")
    assert hasattr(asr, "transcribe")
    assert hasattr(narrative, "generate")
    assert hasattr(structure, "extract")
    assert hasattr(portrait, "generate")


def test_hosted_trace_provider_metadata_exposes_missing_env():
    metadata = hosted_provider.get_provider_metadata()
    assert metadata["implemented"] is False
    assert "HF_TOKEN" in metadata["requires_env"]
    assert "PLE_HF_TRACE_DATASET" in metadata["requires_env"]
    assert "missing_env" in metadata


def test_hosted_trace_provider_raises_actionable_error():
    with pytest.raises(NotImplementedError) as exc:
        hosted_provider.list_saved_runs()
    message = str(exc.value)
    assert "HF_TOKEN" in message
    assert "PLE_HF_TRACE_DATASET" in message
