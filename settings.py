from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
    model_provider: str = "mock"
    demo_mode: bool = True
    traces_provider: str = "local"
    hf_token: str | None = None
    hf_space_id: str | None = None
    hf_trace_dataset: str | None = None
    hf_vision_model: str = "openbmb/MiniCPM-V-4_6"
    hf_asr_model: str = "openai/whisper-small"
    hf_narrative_model: str = "openbmb/MiniCPM5-1B"
    hf_structure_model: str = "openbmb/MiniCPM5-1B"
    hf_portrait_model: str = "black-forest-labs/FLUX.2-KONtext-klein"
    hf_device: str = "auto"
    hf_dtype: str = "auto"
    hf_offload_between_steps: bool = True
    hf_low_cpu_mem_usage: bool = True


def load_settings() -> RuntimeSettings:
    provider = os.getenv("PLE_MODEL_PROVIDER", "mock").strip().lower() or "mock"
    demo_mode = os.getenv("PLE_DEMO_MODE", "true").strip().lower() not in {"0", "false", "no"}
    traces_provider = os.getenv("PLE_TRACES_PROVIDER", "local").strip().lower() or "local"
    return RuntimeSettings(
        model_provider=provider,
        demo_mode=demo_mode,
        traces_provider=traces_provider,
        hf_token=os.getenv("HF_TOKEN"),
        hf_space_id=os.getenv("PLE_HF_SPACE_ID"),
        hf_trace_dataset=os.getenv("PLE_HF_TRACE_DATASET"),
        hf_vision_model=os.getenv("PLE_HF_VISION_MODEL", "openbmb/MiniCPM-V-4_6"),
        hf_asr_model=os.getenv("PLE_HF_ASR_MODEL", "openai/whisper-small"),
        hf_narrative_model=os.getenv("PLE_HF_NARRATIVE_MODEL", "openbmb/MiniCPM5-1B"),
        hf_structure_model=os.getenv("PLE_HF_STRUCTURE_MODEL", "openbmb/MiniCPM5-1B"),
        hf_portrait_model=os.getenv("PLE_HF_PORTRAIT_MODEL", "black-forest-labs/FLUX.2-KONtext-klein"),
        hf_device=os.getenv("PLE_HF_DEVICE", "auto").strip().lower() or "auto",
        hf_dtype=os.getenv("PLE_HF_DTYPE", "auto").strip().lower() or "auto",
        hf_offload_between_steps=os.getenv("PLE_HF_OFFLOAD_BETWEEN_STEPS", "true").strip().lower()
        not in {"0", "false", "no"},
        hf_low_cpu_mem_usage=os.getenv("PLE_HF_LOW_CPU_MEM_USAGE", "true").strip().lower()
        not in {"0", "false", "no"},
    )


SETTINGS = load_settings()
