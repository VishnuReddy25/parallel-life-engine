from __future__ import annotations

from settings import SETTINGS


def get_trace_provider_module():
    if SETTINGS.traces_provider == "local":
        from pipeline.trace_providers import local_provider

        return local_provider

    if SETTINGS.traces_provider in {"hf", "hosted", "huggingface"}:
        from pipeline.trace_providers import hosted_provider

        return hosted_provider

    raise NotImplementedError(
        f"Unsupported traces provider '{SETTINGS.traces_provider}'. "
        "Use 'local' or add a provider implementation."
    )
