from __future__ import annotations

from models.provider_registry import get_provider_module


def get_flux():
    return get_provider_module().get_flux()
