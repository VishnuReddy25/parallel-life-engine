from __future__ import annotations

from pathlib import Path

from pipeline.orchestrator import LifeState
from settings import SETTINGS


def get_provider_metadata() -> dict[str, object]:
    return {
        "implemented": False,
        "provider_key": "hosted",
        "requires_env": ["HF_TOKEN", "PLE_HF_TRACE_DATASET"],
        "configured_env": {
            "HF_TOKEN": bool(SETTINGS.hf_token),
            "PLE_HF_TRACE_DATASET": bool(SETTINGS.hf_trace_dataset),
        },
        "missing_env": [
            name
            for name, present in {
                "HF_TOKEN": bool(SETTINGS.hf_token),
                "PLE_HF_TRACE_DATASET": bool(SETTINGS.hf_trace_dataset),
            }.items()
            if not present
        ],
    }


def _not_implemented(name: str):
    metadata = get_provider_metadata()
    missing = ", ".join(metadata["missing_env"]) if metadata["missing_env"] else "none"
    raise NotImplementedError(
        f"Hosted trace provider '{name}' is not implemented yet. "
        f"Required env vars: {', '.join(metadata['requires_env'])}. Missing: {missing}."
    )


def persist_run_artifacts(state: LifeState) -> LifeState:
    _not_implemented("persist_run_artifacts")


def list_saved_runs(limit: int = 6) -> list[dict[str, object]]:  # noqa: ARG001
    _not_implemented("list_saved_runs")


def get_keepsake_path(trace_id: str) -> Path | None:  # noqa: ARG001
    _not_implemented("get_keepsake_path")


def get_runs_dir() -> Path:
    _not_implemented("get_runs_dir")
