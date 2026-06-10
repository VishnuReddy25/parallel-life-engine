from __future__ import annotations

from pipeline.trace_provider_registry import get_trace_provider_module


def persist_run_artifacts(state):
    return get_trace_provider_module().persist_run_artifacts(state)


def list_saved_runs(limit: int = 6):
    return get_trace_provider_module().list_saved_runs(limit=limit)


def get_keepsake_path(trace_id: str):
    return get_trace_provider_module().get_keepsake_path(trace_id)


def get_runs_dir():
    return get_trace_provider_module().get_runs_dir()
