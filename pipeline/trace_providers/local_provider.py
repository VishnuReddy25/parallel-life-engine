from __future__ import annotations

import base64
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.orchestrator import LifeState

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"
RUNS_DIR = ARTIFACTS_DIR / "runs"


def persist_run_artifacts(state: LifeState) -> LifeState:
    if not state.export_ready or not state.scrapbook_html:
        return state

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    trace_id = state.trace_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = RUNS_DIR / trace_id
    run_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "trace_id": trace_id,
        "life_title": state.life_title,
        "life_summary": state.life_summary,
        "transcription": state.transcription,
        "language_detected": state.language_detected,
        "timeline": state.timeline or [],
        "yield_log": state.yield_log,
        "errors": state.errors,
        "portrait_failures": state.portrait_failures,
        "portrait_prompts": state.portrait_prompts,
        "life_arc": state.life_arc or {},
        "portraits": _encode_portraits(state),
        "created_at": datetime.now(UTC).isoformat(),
    }

    trace_path = run_dir / "trace.json"
    trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    export_path = run_dir / "keepsake.html"
    export_path.write_text(state.scrapbook_html, encoding="utf-8")

    state.trace_id = trace_id
    state.trace_path = str(trace_path)
    state.export_path = str(export_path)
    return state


def list_saved_runs(limit: int = 6) -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []

    runs: list[dict[str, Any]] = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue

        trace_path = run_dir / "trace.json"
        export_path = run_dir / "keepsake.html"
        if not trace_path.exists() or not export_path.exists():
            continue

        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        runs.append(
            {
                "trace_id": trace.get("trace_id", run_dir.name),
                "life_title": trace.get("life_title") or "Recovered Life",
                "life_summary": trace.get("life_summary") or "A saved unlived memoir.",
                "transcription": trace.get("transcription") or "",
                "created_at": trace.get("created_at") or run_dir.name,
                "timeline_count": len(trace.get("timeline") or []),
                "decade_count": len(trace.get("life_arc") or {}),
                "replay_path": f"/runs/{run_dir.name}",
            }
        )
        if len(runs) >= limit:
            break

    return runs


def get_keepsake_path(trace_id: str) -> Path | None:
    export_path = RUNS_DIR / trace_id / "keepsake.html"
    return export_path if export_path.exists() else None


def get_runs_dir() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def _encode_portraits(state: LifeState) -> dict[str, str]:
    encoded = {}
    for decade, image in state.portraits.items():
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=82)
        encoded[decade] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded
