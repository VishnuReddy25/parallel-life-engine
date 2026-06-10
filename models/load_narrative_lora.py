from __future__ import annotations

from models.provider_registry import get_provider_module


def get_narrative_model():
    return get_provider_module().get_narrative_model()
