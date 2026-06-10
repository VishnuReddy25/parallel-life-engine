from __future__ import annotations

from settings import SETTINGS


def get_provider_module():
    if SETTINGS.model_provider == "mock":
        from models.providers import mock_provider

        return mock_provider

    if SETTINGS.model_provider in {"hf", "huggingface"}:
        from models.providers import hf_provider

        return hf_provider

    raise NotImplementedError(
        f"Unsupported model provider '{SETTINGS.model_provider}'. "
        "Use 'mock' or add a provider implementation."
    )
