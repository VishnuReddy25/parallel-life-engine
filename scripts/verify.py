from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import _serialize_state
from app import _app_metadata
from pipeline.orchestrator import LifeState, run_pipeline
from pipeline.trace_store import get_runs_dir, list_saved_runs, persist_run_artifacts
from providers_manifest import get_provider_manifest
from runtime_validation import get_runtime_validation
from settings import SETTINGS


async def _run_pipeline_smoke() -> None:
    state = LifeState(
        photo=Image.new("RGB", (96, 96), "#c9b59f"),
        fork_text="What if I had moved to Tokyo at 22?",
    )
    snapshots = []
    partial_decade_counts = []
    async for snapshot in run_pipeline(state):
        snapshots.append(snapshot)
        if snapshot.life_arc:
            partial_decade_counts.append(len(snapshot.life_arc))

    final = snapshots[-1]
    assert partial_decade_counts
    assert partial_decade_counts[:5] == [1, 2, 3, 4, 5]
    assert final.life_arc is not None and len(final.life_arc) == 5
    assert final.timeline is not None and len(final.timeline) == 5
    assert final.export_ready is True
    assert final.scrapbook_html is not None and "Recovered Memoir" in final.scrapbook_html
    payload = _serialize_state(final)
    assert "\"life_title\"" in payload
    assert "\"transcription\"" in payload
    final = persist_run_artifacts(final)
    assert final.trace_path is not None
    assert final.export_path is not None
    assert Path(final.trace_path).exists()
    assert Path(final.export_path).exists()


async def _run_audio_smoke() -> None:
    state = LifeState(voice_audio=b"voice-note")
    snapshots = []
    async for snapshot in run_pipeline(state):
        snapshots.append(snapshot)

    final = snapshots[-1]
    assert final.transcription is not None
    assert final.language_detected == "en"


def _check_frontend_assets() -> None:
    base = Path(__file__).resolve().parent.parent / "frontend"
    for name in ["index.html", "style.css", "app.js"]:
        path = base / name
        assert path.exists(), f"missing frontend asset: {name}"
        assert path.read_text(encoding="utf-8").strip(), f"empty frontend asset: {name}"
    index_text = (base / "index.html").read_text(encoding="utf-8")
    assert "{{PAGES_DATA}}" in index_text


def _check_project_manifest() -> None:
    manifest = Path(__file__).resolve().parent.parent / "project-manifest.json"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    assert "\"Parallel Life Engine\"" in text
    assert "\"/meta\"" in text
    assert "\"/providers\"" in text


def _check_schemas() -> None:
    root = Path(__file__).resolve().parent.parent / "schemas"
    assert (root / "project-manifest.schema.json").exists()
    assert (root / "providers-manifest.schema.json").exists()
    assert (root / "runtime-validation.schema.json").exists()
    assert (root / "health-response.schema.json").exists()
    assert (root / "meta-response.schema.json").exists()
    assert (root / "providers-response.schema.json").exists()


def _check_examples_dir() -> None:
    examples = Path(__file__).resolve().parent.parent / "examples"
    if examples.exists():
        names = {path.name for path in examples.iterdir() if path.is_file()}
        expected = {
            "health.example.json",
            "meta.example.json",
            "providers.example.json",
            "runtime-validation.example.json",
        }
        assert expected.issubset(names)


def _check_provider_layout() -> None:
    root = Path(__file__).resolve().parent.parent
    assert (root / "models" / "provider_registry.py").exists()
    assert (root / "models" / "providers" / "mock_provider.py").exists()
    assert (root / "models" / "providers" / "hf_provider.py").exists()
    assert (root / "models" / "provider_contracts.py").exists()
    assert (root / "pipeline" / "trace_provider_registry.py").exists()
    assert (root / "pipeline" / "trace_providers" / "local_provider.py").exists()
    assert (root / "pipeline" / "trace_providers" / "hosted_provider.py").exists()


def _check_artifacts_dir() -> None:
    runs_dir = get_runs_dir()
    assert runs_dir.exists()


def _check_saved_runs_listing() -> None:
    runs = list_saved_runs()
    assert isinstance(runs, list)
    if runs:
        assert "replay_path" in runs[0]


def _check_app_metadata() -> None:
    metadata = _app_metadata()
    assert metadata["app_name"] == "Parallel Life Engine"
    assert "runtime" in metadata
    assert "saved_runs_count" in metadata
    assert "gradio_blocks_ui" in metadata["features"]


def _check_runtime_settings() -> None:
    assert SETTINGS.model_provider in {"mock"}
    assert SETTINGS.traces_provider in {"local"}


def _check_provider_manifest() -> None:
    manifest = get_provider_manifest()
    assert manifest["selected"]["model_provider"] == SETTINGS.model_provider
    assert manifest["selected"]["traces_provider"] == SETTINGS.traces_provider
    assert "hf" in manifest["model_providers"]
    assert "hosted" in manifest["trace_providers"]
    assert manifest["model_providers"]["hf"]["implemented"] is True
    assert "stack" in manifest["model_providers"]["hf"]
    assert manifest["trace_providers"]["hosted"]["implemented"] is False


def _check_runtime_validation() -> None:
    result = get_runtime_validation()
    assert result["selected_model_provider"] == SETTINGS.model_provider
    assert result["selected_traces_provider"] == SETTINGS.traces_provider
    assert result["ok"] is True


def main() -> None:
    _check_frontend_assets()
    _check_project_manifest()
    _check_schemas()
    _check_examples_dir()
    _check_provider_layout()
    _check_artifacts_dir()
    _check_runtime_settings()
    asyncio.run(_run_pipeline_smoke())
    asyncio.run(_run_audio_smoke())
    _check_saved_runs_listing()
    _check_app_metadata()
    _check_provider_manifest()
    _check_runtime_validation()
    print("verify-ok")


if __name__ == "__main__":
    main()
