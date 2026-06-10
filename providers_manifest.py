from __future__ import annotations

from typing import Any

from pipeline.trace_providers import hosted_provider, local_provider
from models.providers import hf_provider
from settings import SETTINGS


def get_provider_manifest() -> dict[str, Any]:
    return {
        "selected": {
            "model_provider": SETTINGS.model_provider,
            "traces_provider": SETTINGS.traces_provider,
        },
        "model_providers": {
            "mock": {
                "implemented": True,
                "requires_env": [],
                "notes": "Fully local demo-mode provider stack.",
            },
            "hf": hosted_model_manifest(),
        },
        "trace_providers": {
            "local": {
                "implemented": True,
                "requires_env": [],
                "notes": "Filesystem-backed run artifacts under artifacts/runs/.",
            },
            "hosted": hosted_trace_manifest(),
        },
    }


def hosted_model_manifest() -> dict[str, Any]:
    return hf_provider.get_provider_metadata()


def hosted_trace_manifest() -> dict[str, Any]:
    return hosted_provider.get_provider_metadata()
