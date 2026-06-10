from __future__ import annotations

from models.provider_registry import get_provider_module


def get_minicpm_v():
    return get_provider_module().get_minicpm_v()
