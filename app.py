from __future__ import annotations

import base64
import json
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from pipeline.orchestrator import LifeState, run_pipeline
from pipeline.trace_store import list_saved_runs, persist_run_artifacts
from runtime_validation import get_runtime_validation
from settings import SETTINGS

try:
    import gradio as gr
except ModuleNotFoundError:  # pragma: no cover
    gr = None

try:
    import spaces
except ModuleNotFoundError:  # pragma: no cover
    class _SpacesShim:
        @staticmethod
        def GPU(fn):
            return fn

    spaces = _SpacesShim()


def _serialize_state(state: LifeState) -> str:
    payload = {
        "log": state.yield_log[-1] if state.yield_log else "",
        "errors": state.errors,
        "decades": state.decades,
        "life_title": state.life_title,
        "life_summary": state.life_summary,
        "transcription": state.transcription,
        "language_detected": state.language_detected,
        "trace_id": state.trace_id,
        "trace_path": state.trace_path,
        "export_path": state.export_path,
        "life_arc": state.life_arc or {},
        "timeline": state.timeline or [],
        "portrait_failures": state.portrait_failures,
        "portraits": {},
        "portraits_ready": list(state.portraits.keys()),
        "narrative_ready": list((state.life_arc or {}).keys()),
        "export_ready": state.export_ready,
        "scrapbook_html": state.scrapbook_html if state.export_ready else None,
        "runtime": {
            "model_provider": SETTINGS.model_provider,
            "demo_mode": SETTINGS.demo_mode,
            "traces_provider": SETTINGS.traces_provider,
        },
    }
    for decade, image in state.portraits.items():
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=82)
        payload["portraits"][decade] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return json.dumps(payload)


def _app_metadata() -> dict[str, object]:
    saved_runs = list_saved_runs(limit=20)
    return {
        "app_name": "Parallel Life Engine",
        "runtime": {
            "model_provider": SETTINGS.model_provider,
            "demo_mode": SETTINGS.demo_mode,
            "traces_provider": SETTINGS.traces_provider,
        },
        "features": [
            "typed_fork_input",
            "voice_fork_input",
            "progressive_narrative_reveal",
            "progressive_portrait_reveal",
            "exportable_keepsake",
            "saved_run_replay",
            "runtime_diagnostics",
            "gradio_blocks_ui",
        ],
        "saved_runs_count": len(saved_runs),
        "runtime_validation": get_runtime_validation(),
    }


def _saved_runs_markdown() -> str:
    runs = list_saved_runs()
    if not runs:
        return "No saved lives yet. Run one reconstruction and it will appear here."
    return "\n".join(
        f"**{run['life_title']}**  \n{run['life_summary']}  \n[Replay]({run['replay_path']})"
        for run in runs
    )


def _timeline_markdown(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Anchor memories will appear here as the life settles into structure."
    return "\n".join(
        f"**{item.get('decade', 'Memory')}**  \n{item.get('event', 'Untitled event')}  \n*{item.get('location', 'unknown place')}*"
        for item in items[:5]
    )


def _errors_markdown(errors: list[str], portrait_failures: list[str]) -> str:
    combined = [*(errors or []), *(portrait_failures or [])]
    if not combined:
        return "No visible fractures yet."
    return "\n".join(f"- {item}" for item in combined)


def _build_gallery_items(payload: dict[str, Any]) -> list[tuple[Image.Image, str]]:
    items: list[tuple[Image.Image, str]] = []
    portraits = payload.get("portraits") or {}
    for decade in payload.get("decades") or []:
        encoded = portraits.get(decade)
        if not encoded:
            continue
        image = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGB")
        details = (payload.get("life_arc") or {}).get(decade, {})
        caption = f"{decade}  |  {details.get('location', 'unknown')}  |  {details.get('emotion', 'memory')}"
        items.append((image, caption))
    return items


def _build_narrative_markdown(payload: dict[str, Any]) -> str:
    life_arc = payload.get("life_arc") or {}
    if not life_arc:
        return "The memoir will appear here decade by decade."
    sections = []
    for decade in payload.get("decades") or ["20s", "30s", "40s", "50s", "60s"]:
        details = life_arc.get(decade)
        if not details:
            continue
        sections.append(
            f"## {decade}\n"
            f"**{details.get('key_event', 'Turning point')}**  \n"
            f"{details.get('narrative', '')}  \n\n"
            f"**Relationship**: {details.get('relationship', '')}  \n"
            f"**Body memory**: {details.get('physical_memory', '')}  \n"
            f"**Aftertaste**: {details.get('aftertaste', '')}"
        )
    return "\n\n".join(sections)


def _runtime_markdown() -> str:
    runtime = _app_metadata()["runtime"]
    validation = _app_metadata()["runtime_validation"]
    lines = [
        f"**Models**: `{runtime['model_provider']}`",
        f"**Demo mode**: `{runtime['demo_mode']}`",
        f"**Traces**: `{runtime['traces_provider']}`",
    ]
    if validation["ok"]:
        lines.append("**Validation**: `ok`")
    else:
        lines.extend(f"- {issue}" for issue in validation["issues"])
    return "\n\n".join(lines)


def _write_temp_html(html: str | None) -> str | None:
    if not html:
        return None
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    handle.write(html.encode("utf-8"))
    handle.close()
    return handle.name


def _initial_payload() -> dict[str, Any]:
    return {
        "log": "",
        "life_arc": {},
        "timeline": [],
        "portraits_ready": [],
        "narrative_ready": [],
        "export_ready": False,
        "runtime": {
            "model_provider": SETTINGS.model_provider,
            "demo_mode": SETTINGS.demo_mode,
            "traces_provider": SETTINGS.traces_provider,
        },
    }


def _stage_items(payload: dict[str, Any]) -> list[tuple[str, str]]:
    log = payload.get("log", "")
    ready_decades = len(payload.get("narrative_ready") or [])
    ready_portraits = len(payload.get("portraits_ready") or [])
    export_ready = bool(payload.get("export_ready"))
    return [
        ("Fork Intake", "done" if "start:asr" in log or payload.get("transcription") else "idle"),
        ("Memoir", "done" if ready_decades >= 5 else "active" if ready_decades else "idle"),
        ("Timeline", "done" if payload.get("timeline") else "active" if "done:narrative" in log else "idle"),
        ("Portraits", "done" if ready_portraits >= 3 else "active" if ready_portraits else "idle"),
        ("Export", "done" if export_ready else "active" if "start:export" in log else "idle"),
    ]


def _render_progress_html(payload: dict[str, Any]) -> str:
    stages = _stage_items(payload)
    step_classes = []
    for label, state in stages:
        step_classes.append(
            f"<div class='ple-stage-card {state}'><span class='ple-stage-dot'></span><div><strong>{label}</strong><small>{state.upper()}</small></div></div>"
        )
    return (
        "<div class='ple-command-center'>"
        "<div class='ple-command-label'>AI Command Center</div>"
        "<div class='ple-command-grid'>"
        + "".join(step_classes)
        + "</div></div>"
    )


def _render_metrics_html(payload: dict[str, Any]) -> str:
    ready_decades = len(payload.get("narrative_ready") or [])
    ready_portraits = len(payload.get("portraits_ready") or [])
    timeline_count = len(payload.get("timeline") or [])
    runtime = payload.get("runtime") or _initial_payload()["runtime"]
    stats = [
        ("Decades", f"{ready_decades}/5"),
        ("Portraits", str(ready_portraits)),
        ("Timeline Nodes", str(timeline_count)),
        ("Runtime", str(runtime.get("model_provider", "mock")).upper()),
    ]
    return "<div class='ple-stats-grid'>" + "".join(
        f"<div class='ple-stat-card'><span>{label}</span><strong>{value}</strong></div>" for label, value in stats
    ) + "</div>"


def _render_activity_html(payload: dict[str, Any]) -> str:
    log = payload.get("log") or "idle"
    ready_decades = payload.get("narrative_ready") or []
    ready_portraits = payload.get("portraits_ready") or []
    items = [
        f"<div class='ple-feed-item'><span class='pulse'></span><div><strong>Engine</strong><small>{log}</small></div></div>",
        f"<div class='ple-feed-item'><span class='pulse'></span><div><strong>Decades Ready</strong><small>{', '.join(ready_decades) or 'waiting'}</small></div></div>",
        f"<div class='ple-feed-item'><span class='pulse'></span><div><strong>Portrait Queue</strong><small>{', '.join(ready_portraits) or 'warming up'}</small></div></div>",
    ]
    return "<div class='ple-activity-feed'>" + "".join(items) + "</div>"


def _render_insights_html(payload: dict[str, Any]) -> str:
    life_arc = payload.get("life_arc") or {}
    if not life_arc:
        return (
            "### Narrative Intelligence\n"
            "The insights workspace will surface emotional motifs, anchor places, and relationship threads as soon as the memoir begins to form."
        )
    locations = [data.get("location", "Unknown") for data in life_arc.values()[:3]]
    emotions = [data.get("emotion", "memory") for data in life_arc.values()[:3]]
    return (
        "### Narrative Intelligence\n"
        f"- **Dominant places:** {', '.join(locations)}\n"
        f"- **Emotional weather:** {', '.join(emotions)}\n"
        f"- **Memoir depth:** {len(life_arc)}/5 decades recovered\n"
        "- **Investor hook:** this output feels like an artifact, not a chatbot response."
    )


CUSTOM_CSS = """
:root {
  --bg-1: #efe2cd;
  --bg-2: #dcc2a3;
  --ink: #18120f;
  --muted: #6a5a51;
  --accent: #a4512d;
  --accent-deep: #76331f;
  --gold: #d6902b;
  --panel: rgba(250, 244, 236, 0.92);
  --line: rgba(93, 64, 44, 0.16);
  --shadow: rgba(31, 20, 15, 0.18);
  --stage: #1d1816;
  --stage-soft: #29211e;
  --stage-line: rgba(255, 238, 219, 0.08);
  --stage-text: #f7ead6;
}

body, .gradio-container {
  background:
    radial-gradient(circle at top left, rgba(233, 183, 97, 0.24), transparent 24%),
    radial-gradient(circle at 86% 10%, rgba(168, 85, 46, 0.14), transparent 16%),
    linear-gradient(180deg, #f2e6d4 0%, #e5d3bb 48%, #d6bea0 100%);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif !important;
}

.gradio-container {
  max-width: 1480px !important;
  padding: 22px 16px 30px !important;
}

#ple-shell {
  background:
    linear-gradient(180deg, rgba(255,255,255,0.48), rgba(255,255,255,0.16)),
    rgba(245, 233, 216, 0.78);
  border: 1px solid rgba(113, 78, 52, 0.12);
  border-radius: 34px;
  box-shadow: 0 30px 84px var(--shadow);
  overflow: hidden;
}

.ple-hero {
  padding: 54px 54px 38px;
  background:
    linear-gradient(126deg, rgba(28, 22, 19, 0.98), rgba(72, 42, 31, 0.95) 42%, rgba(157, 82, 47, 0.88)),
    radial-gradient(circle at top left, rgba(255, 213, 152, 0.14), transparent 22%);
  color: #fff8ef;
}

.ple-kicker {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  opacity: 0.76;
  margin-bottom: 16px;
}

.ple-hero h1 {
  margin: 0;
  font-size: 68px;
  line-height: 0.9;
  letter-spacing: -0.04em;
}

.ple-hero p {
  max-width: 860px;
  margin: 18px 0 0;
  font-size: 19px;
  line-height: 1.66;
  color: rgba(255, 242, 226, 0.9);
}

.ple-band {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 26px;
}

.ple-chip {
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 248, 238, 0.1);
  border: 1px solid rgba(255, 248, 238, 0.15);
  color: #fff4e8;
  font-size: 12px;
}

.ple-section {
  padding: 22px 24px 8px;
}

.ple-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: 0 16px 38px rgba(72, 41, 27, 0.08);
}

#runtime-card {
  background:
    radial-gradient(circle at top left, rgba(214, 137, 69, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(39,29,24,0.98), rgba(26,20,18,0.99));
  border-color: rgba(255, 237, 218, 0.08);
}

.ple-input,
.ple-runtime,
.ple-output {
  padding: 28px;
}

.ple-subhead {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 10px;
}

.ple-title {
  margin: 0 0 12px;
  font-size: 34px;
  line-height: 1.03;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.ple-blurb {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
  font-size: 15px;
}

#runtime-card .ple-subhead {
  color: #f2bb76;
}

#runtime-card .ple-title,
#runtime-card .ple-blurb,
#runtime-card .gr-markdown,
#runtime-card .gr-markdown *,
#runtime-card p,
#runtime-card span,
#runtime-card label,
#runtime-card strong {
  color: var(--stage-text) !important;
  opacity: 1 !important;
}

.ple-card .gr-markdown,
.ple-card .gr-markdown *,
.ple-card p,
.ple-card h1,
.ple-card h2,
.ple-card h3,
.ple-card h4,
.ple-card li,
.ple-card span,
.ple-card label,
.ple-card strong {
  color: var(--ink) !important;
  opacity: 1 !important;
}

.gr-button-primary {
  background: linear-gradient(135deg, var(--accent-deep), #bf6d3b) !important;
  border: none !important;
  color: #fff8ef !important;
  min-height: 48px !important;
  font-weight: 700 !important;
  box-shadow: 0 12px 24px rgba(124, 56, 32, 0.24) !important;
}

.gr-button-secondary, .gr-button {
  border-radius: 16px !important;
}

.gr-box, .gr-panel, .gr-form, .gr-group, .gradio-group {
  border-radius: 20px !important;
}

.ple-card .gradio-image,
.ple-card .gradio-audio,
.ple-card .gr-gallery,
.ple-card .gr-file,
.ple-card .gr-code,
.ple-card .gr-accordion {
  background: transparent !important;
}

.ple-card textarea,
.ple-card input,
.ple-card .gr-textbox,
.ple-card .gr-textbox textarea,
.ple-card .gr-textbox input {
  background: rgba(255, 249, 241, 0.96) !important;
  color: var(--ink) !important;
  border: 1px solid rgba(121, 82, 54, 0.16) !important;
}

#runtime-card textarea,
#runtime-card input,
#runtime-card .gr-textbox,
#runtime-card .gr-textbox textarea,
#runtime-card .gr-textbox input {
  background: rgba(255,255,255,0.08) !important;
  color: var(--stage-text) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
}

.ple-card .image-container,
.ple-card .audio-container,
.ple-card .empty,
.ple-card .wrap,
.ple-card .file-preview,
.ple-card .cm-editor,
.ple-card .cm-scroller,
.ple-card .gallery-container {
  background: var(--stage) !important;
  color: #f8efe5 !important;
  border: 1px solid var(--stage-line) !important;
  border-radius: 22px !important;
}

.ple-card .empty,
.ple-card .image-container .placeholder,
.ple-card .audio-container .placeholder {
  color: #f6ebde !important;
}

.ple-card .label-wrap {
  margin-bottom: 10px !important;
}

.ple-card .label-wrap label {
  display: inline-block;
  background: linear-gradient(135deg, var(--gold), #cd741b);
  color: #fff8ef !important;
  padding: 7px 12px;
  border-radius: 10px;
  font-weight: 700;
}

.ple-card .icon-button {
  background: transparent !important;
  color: #f0bf74 !important;
}

.ple-card .gallery-item {
  border-radius: 18px !important;
  overflow: hidden;
}

.ple-card .gallery-item img {
  filter: saturate(0.95) contrast(1.02);
}

.ple-card .accordion-header {
  background: var(--stage) !important;
  color: #fff5e8 !important;
}

.ple-card .accordion-body {
  background: rgba(248, 242, 234, 0.98) !important;
}

.ple-card .gr-markdown h2 {
  font-size: 30px !important;
  letter-spacing: -0.02em;
}

.ple-card .gr-markdown h3 {
  font-size: 24px !important;
}

.ple-card .gr-markdown p,
.ple-card .gr-markdown li {
  font-size: 15px !important;
  line-height: 1.72 !important;
}

.ple-card .gr-markdown a {
  color: var(--accent-deep) !important;
  font-weight: 700;
}

.ple-card .gr-file .file-preview {
  background: linear-gradient(180deg, rgba(255,252,247,0.95), rgba(249,240,227,0.95)) !important;
  color: var(--ink) !important;
  border: 1px solid rgba(121, 82, 54, 0.14) !important;
}

.ple-card .gr-examples .example {
  border-radius: 999px !important;
  border: 1px solid rgba(121, 82, 54, 0.18) !important;
  background: rgba(255, 251, 246, 0.9) !important;
  color: var(--ink) !important;
}

.ple-footer-note {
  padding: 6px 34px 34px;
  color: var(--muted);
  font-size: 13px;
}

.ple-dashboard {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 0;
}

.ple-sidebar {
  min-height: 100%;
  padding: 26px 18px;
  border-right: 1px solid rgba(108, 75, 50, 0.1);
  background: linear-gradient(180deg, rgba(40,29,24,0.98), rgba(27,21,18,0.98));
}

.ple-side-brand {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  color: #fff6eb;
}

.ple-side-brand strong {
  display: block;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.ple-side-brand span {
  display: block;
  margin-top: 6px;
  color: rgba(255, 239, 220, 0.66);
  font-size: 13px;
  line-height: 1.5;
}

.ple-side-nav {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}

.ple-nav-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  color: #fff1e0;
}

.ple-nav-item strong {
  display: block;
  font-size: 14px;
}

.ple-nav-item small {
  display: block;
  margin-top: 4px;
  color: rgba(255, 238, 218, 0.58);
}

.ple-side-tip {
  margin-top: 18px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  color: #f3e1cf;
  font-size: 13px;
  line-height: 1.6;
}

.ple-side-tip code {
  background: rgba(255,255,255,0.08);
  color: #fff4e7;
  padding: 0.16rem 0.4rem;
  border-radius: 8px;
}

.ple-main {
  min-width: 0;
}

.ple-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 0 24px 6px;
}

.ple-stat-card {
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255,255,255,0.42);
  border: 1px solid rgba(116, 79, 50, 0.1);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.45);
}

.ple-stat-card span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.ple-stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: var(--ink);
  letter-spacing: -0.03em;
}

.ple-command-center {
  margin-bottom: 18px;
}

.ple-command-label {
  margin-bottom: 12px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: #f0bd76;
}

.ple-command-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.ple-stage-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 14px;
  border-radius: 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
}

.ple-stage-card strong {
  display: block;
  color: #fff5e7;
  font-size: 14px;
}

.ple-stage-card small {
  display: block;
  margin-top: 3px;
  color: rgba(255, 240, 221, 0.58);
  letter-spacing: 0.12em;
  font-size: 10px;
}

.ple-stage-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.2);
  box-shadow: 0 0 0 6px rgba(255,255,255,0.02);
}

.ple-stage-card.active .ple-stage-dot {
  background: #f0b86f;
  box-shadow: 0 0 0 6px rgba(240, 184, 111, 0.12);
}

.ple-stage-card.done .ple-stage-dot {
  background: #43c47f;
  box-shadow: 0 0 0 6px rgba(67, 196, 127, 0.12);
}

.ple-activity-feed {
  display: grid;
  gap: 10px;
}

.ple-feed-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.05);
}

.ple-feed-item strong {
  display: block;
  color: #fff4e7 !important;
  font-size: 13px;
}

.ple-feed-item small {
  display: block;
  margin-top: 3px;
  color: rgba(255, 240, 222, 0.58);
}

.pulse {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #f0b86f;
  box-shadow: 0 0 0 0 rgba(240, 184, 111, 0.45);
  animation: ple-pulse 1.8s infinite;
}

@keyframes ple-pulse {
  0% { box-shadow: 0 0 0 0 rgba(240, 184, 111, 0.45); }
  70% { box-shadow: 0 0 0 12px rgba(240, 184, 111, 0); }
  100% { box-shadow: 0 0 0 0 rgba(240, 184, 111, 0); }
}

@media (max-width: 980px) {
  .ple-dashboard {
    grid-template-columns: 1fr;
  }

  .ple-sidebar {
    border-right: 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }

  .ple-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0 16px 6px;
  }

  .gradio-container {
    padding: 12px 8px 20px !important;
  }

  .ple-hero {
    padding: 34px 24px 24px;
  }

  .ple-hero h1 {
    font-size: 46px;
  }

  .ple-title {
    font-size: 30px;
  }

  .ple-section {
    padding: 16px 14px 6px;
  }
}
"""


HERO_HTML = """
<section class="ple-hero">
  <div class="ple-kicker">Build Small / Thousand Token Wood / Spectacle-First Memoir Engine</div>
  <h1>Parallel Life Engine</h1>
  <p>
    A machine for mourning the lives you never lived. Begin with one portrait and one impossible sentence,
    then watch an unlived memoir assemble itself into decades, portraits, anchor memories, and a keepsake export.
  </p>
  <div class="ple-band">
    <div class="ple-chip">Portrait In</div>
    <div class="ple-chip">Fork Sentence</div>
    <div class="ple-chip">Five Decades</div>
    <div class="ple-chip">Portrait Reveal</div>
    <div class="ple-chip">Keepsake Out</div>
  </div>
</section>
"""


SIDEBAR_HTML = """
<aside class="ple-sidebar">
  <div class="ple-side-brand">
    <strong>Parallel Life Engine</strong>
    <span>The alternate-life operating system.</span>
  </div>
  <div class="ple-side-nav">
    <div class="ple-nav-item"><strong>Input Studio</strong><small>portrait + fork sentence</small></div>
    <div class="ple-nav-item"><strong>Command Center</strong><small>live orchestration state</small></div>
    <div class="ple-nav-item"><strong>Memoir Workspace</strong><small>decades, portraits, narrative value</small></div>
    <div class="ple-nav-item"><strong>Replay Shelf</strong><small>artifact library</small></div>
  </div>
  <div class="ple-side-tip">
    <strong>Fast trigger</strong><br/>
    Use a fork sentence with a real place, a real age, or a real unrealized desire. It creates much stronger output.<br/><br/>
    <strong>Shortcut</strong><br/>Press <code>Ctrl</code> + <code>Enter</code> to run.
  </div>
</aside>
<script>
document.addEventListener("keydown", function(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    const button = document.getElementById("generate-btn");
    if (button) {
      button.click();
    }
  }
});
</script>
"""


SPACE_THEME = (
    gr.themes.Soft(
        primary_hue="amber",
        secondary_hue="rose",
        neutral_hue="stone",
    )
    if gr is not None
    else None
)


@spaces.GPU
async def _run_for_gradio(photo: Image.Image | None, audio_path: str | None, fork_text: str | None):
    audio_bytes = Path(audio_path).read_bytes() if audio_path else None
    state = LifeState(
        photo=photo.convert("RGB") if photo else None,
        voice_audio=audio_bytes,
        fork_text=(fork_text or "").strip() or None,
    )
    final_state = state
    async for snapshot in run_pipeline(state):
        final_state = snapshot
        payload = json.loads(_serialize_state(snapshot))
        yield (
            _render_progress_html(payload),
            _render_metrics_html(payload),
            _render_activity_html(payload),
            payload.get("log") or "Listening for the next clue.",
            payload.get("life_title") or "The Life Where I Turned",
            payload.get("life_summary") or "A memoir of the choice that kept unfolding.",
            payload.get("transcription") or "",
            _runtime_markdown(),
            _render_insights_html(payload),
            _build_narrative_markdown(payload),
            _timeline_markdown(payload.get("timeline") or []),
            _build_gallery_items(payload),
            _errors_markdown(payload.get("errors") or [], payload.get("portrait_failures") or []),
            gr.update(value=_write_temp_html(payload.get("scrapbook_html")), visible=bool(payload.get("export_ready"))),
            _saved_runs_markdown(),
            json.dumps(payload, indent=2),
        )

    persist_run_artifacts(final_state)
    final_payload = json.loads(_serialize_state(final_state))
    yield (
        _render_progress_html(final_payload),
        _render_metrics_html(final_payload),
        _render_activity_html(final_payload),
        final_payload.get("log") or "Recovered memoir complete.",
        final_payload.get("life_title") or "The Life Where I Turned",
        final_payload.get("life_summary") or "A memoir of the choice that kept unfolding.",
        final_payload.get("transcription") or "",
        _runtime_markdown(),
        _render_insights_html(final_payload),
        _build_narrative_markdown(final_payload),
        _timeline_markdown(final_payload.get("timeline") or []),
        _build_gallery_items(final_payload),
        _errors_markdown(final_payload.get("errors") or [], final_payload.get("portrait_failures") or []),
        gr.update(value=_write_temp_html(final_payload.get("scrapbook_html")), visible=bool(final_payload.get("export_ready"))),
        _saved_runs_markdown(),
        json.dumps(final_payload, indent=2),
    )


def _build_demo():
    if gr is None:
        return None

    initial_payload = _initial_payload()

    with gr.Blocks(title="Parallel Life Engine") as demo:
        gr.HTML(f"<style>{CUSTOM_CSS}</style>")
        with gr.Column(elem_id="ple-shell"):
            with gr.Row(elem_classes=["ple-dashboard"]):
                with gr.Column(scale=2, min_width=220):
                    gr.HTML(SIDEBAR_HTML)

                with gr.Column(scale=10, elem_classes=["ple-main"]):
                    gr.HTML(HERO_HTML)
                    metrics = gr.HTML(_render_metrics_html(initial_payload))

                    with gr.Row(elem_classes=["ple-section"], equal_height=True):
                        with gr.Column(scale=6, elem_classes=["ple-card"], elem_id="input-card"):
                            gr.HTML(
                                """
                                <div class="ple-input">
                                  <div class="ple-subhead">Input Studio</div>
                                  <h2 class="ple-title">Feed the machine one face and one impossible sentence.</h2>
                                  <p class="ple-blurb">Use one portrait and one fork in the road. Voice is optional. The sentence is the real ignition key.</p>
                                </div>
                                """
                            )
                            photo = gr.Image(type="pil", label="Portrait Photo", height=410)
                            with gr.Row():
                                audio = gr.Audio(type="filepath", label="Voice Fork", sources=["upload", "microphone"], scale=4)
                                fork_text = gr.Textbox(
                                    label="Life Fork",
                                    lines=8,
                                    placeholder="What if I had moved to Tokyo at 22 and stayed long enough to become a photographer?",
                                    scale=5,
                                )
                            with gr.Row():
                                generate = gr.Button("Reconstruct Life", variant="primary", scale=2, elem_id="generate-btn")
                                export_file = gr.File(label="Keepsake Export", visible=False, scale=1)
                            gr.Examples(
                                examples=[
                                    ["What if I had moved to Tokyo at 22 and stayed long enough to become a photographer?"],
                                    ["What if I had joined an indie band in Sao Paulo instead of taking the safe office job?"],
                                    ["What if I had accepted the marine biology fellowship and spent my life near the sea?"],
                                ],
                                inputs=[fork_text],
                            )

                        with gr.Column(scale=4, elem_classes=["ple-card", "ple-runtime"], elem_id="runtime-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">Command Center</div>
                                <h2 class="ple-title">Watch the reconstruction happen.</h2>
                                <p class="ple-blurb">Live orchestration state, stage transitions, and runtime integrity all in one place.</p>
                                """
                            )
                            progress = gr.HTML(_render_progress_html(initial_payload))
                            activity = gr.HTML(_render_activity_html(initial_payload))
                            status = gr.Markdown("Listening for the next clue.")
                            title = gr.Markdown("## The Life Where I Turned")
                            summary = gr.Markdown("A memoir of the choice that kept unfolding.")
                            transcription = gr.Textbox(label="Recovered Fork", interactive=False)
                            runtime = gr.Markdown(_runtime_markdown())
                            errors = gr.Markdown("No visible fractures yet.")

                    with gr.Row(elem_classes=["ple-section"], equal_height=True):
                        with gr.Column(scale=7, elem_classes=["ple-card", "ple-output"], elem_id="memoir-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">Memoir Workspace</div>
                                <h2 class="ple-title">The unlived scrapbook</h2>
                                <p class="ple-blurb">This is the emotional center of the experience. Each decade should feel literary, specific, and painfully plausible.</p>
                                """
                            )
                            narrative = gr.Markdown("The memoir will appear here decade by decade.")

                        with gr.Column(scale=5, elem_classes=["ple-card", "ple-output"], elem_id="gallery-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">Portrait Reel</div>
                                <h2 class="ple-title">The face the years might have made</h2>
                                <p class="ple-blurb">Portraits should land like emotional reveals, not like utility thumbnails.</p>
                                """
                            )
                            gallery = gr.Gallery(label="Decade Portraits", columns=2, height=720, object_fit="cover")

                    with gr.Row(elem_classes=["ple-section"], equal_height=True):
                        with gr.Column(scale=4, elem_classes=["ple-card", "ple-output"], elem_id="insights-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">AI Insights</div>
                                <h2 class="ple-title">Narrative intelligence</h2>
                                <p class="ple-blurb">Live narrative signals, emotional motifs, and investor-friendly value framing.</p>
                                """
                            )
                            insights = gr.Markdown(_render_insights_html(initial_payload))

                        with gr.Column(scale=4, elem_classes=["ple-card", "ple-output"], elem_id="timeline-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">Activity Timeline</div>
                                <h2 class="ple-title">Anchor memories</h2>
                                <p class="ple-blurb">A structured readout of the alternate life arc for fast scanning during the demo.</p>
                                """
                            )
                            timeline = gr.Markdown("Anchor memories will appear here as the life settles into structure.")

                        with gr.Column(scale=4, elem_classes=["ple-card", "ple-output"], elem_id="shelf-card"):
                            gr.HTML(
                                """
                                <div class="ple-subhead">Replay Shelf</div>
                                <h2 class="ple-title">Recovered lives</h2>
                                <p class="ple-blurb">Saved runs make the app feel like a collection of parallel selves instead of a one-shot output.</p>
                                """
                            )
                            saved_runs = gr.Markdown(_saved_runs_markdown())

                    with gr.Accordion("Raw Streaming Snapshot", open=False, elem_classes=["ple-section"]):
                        raw = gr.Code(label="Streaming Snapshot", language="json")

                    gr.HTML(
                        """
                        <div class="ple-footer-note">
                          Build Small note: the app is designed as a chain of small specialist stages rather than one monolithic model response.
                        </div>
                        """
                    )

        generate.click(
            fn=_run_for_gradio,
            inputs=[photo, audio, fork_text],
            outputs=[
                progress,
                metrics,
                activity,
                status,
                title,
                summary,
                transcription,
                runtime,
                insights,
                narrative,
                timeline,
                gallery,
                errors,
                export_file,
                saved_runs,
                raw,
            ],
        )

    return demo


demo = _build_demo()
app = demo


if __name__ == "__main__" and demo is not None:  # pragma: no cover
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        theme=SPACE_THEME,
    )
