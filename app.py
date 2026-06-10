from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from pipeline.orchestrator import LifeState, run_pipeline
from pipeline.trace_store import get_keepsake_path, list_saved_runs, persist_run_artifacts
from providers_manifest import get_provider_manifest
from runtime_validation import get_runtime_validation
from settings import SETTINGS

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

try:
    import gradio as gr
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    gr = None

try:
    import spaces
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    class _SpacesShim:
        @staticmethod
        def GPU(fn):
            return fn

    spaces = _SpacesShim()

try:
    from fastapi import FastAPI, File, Form, UploadFile
    from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    FastAPI = None
    File = Form = UploadFile = None


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


async def stream_run(photo: UploadFile | None, audio: UploadFile | None, fork_text: str | None):
    image = None
    if photo is not None:
        image_bytes = await photo.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

    audio_bytes = None
    if audio is not None:
        audio_bytes = await audio.read()

    state = LifeState(
        photo=image,
        voice_audio=audio_bytes,
        fork_text=fork_text,
    )

    final_state = state
    async for updated_state in run_pipeline(state):
        final_state = updated_state
        yield _serialize_state(updated_state) + "\n"

    persist_run_artifacts(final_state)
    if final_state.export_ready:
        yield _serialize_state(final_state) + "\n"


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
        return "No recovered lives on the shelf yet."
    lines = []
    for run in runs:
        lines.append(
            f"- **{run['life_title']}**  \n"
            f"  {run['life_summary']}  \n"
            f"  [Replay]({run['replay_path']})"
        )
    return "\n".join(lines)


def _timeline_markdown(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Timeline notes will appear here."
    lines = []
    for item in items[:5]:
        lines.append(
            f"- **{item.get('decade', 'Memory')}**: {item.get('event', 'Untitled event')} "
            f"({item.get('location', 'unknown place')})"
        )
    return "\n".join(lines)


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
        caption = f"{decade} - {details.get('location', 'unknown')} - {details.get('emotion', 'memory')}"
        items.append((image, caption))
    return items


def _build_narrative_markdown(payload: dict[str, Any]) -> str:
    life_arc = payload.get("life_arc") or {}
    if not life_arc:
        return "Your unlived memoir will stream in decade by decade."
    sections = []
    for decade in payload.get("decades") or ["20s", "30s", "40s", "50s", "60s"]:
        details = life_arc.get(decade)
        if not details:
            continue
        sections.append(
            f"### {decade}\n"
            f"**{details.get('key_event', 'Turning point')}**  \n"
            f"{details.get('narrative', '')}  \n"
            f"*Relationship:* {details.get('relationship', '')}  \n"
            f"*Body memory:* {details.get('physical_memory', '')}  \n"
            f"*Aftertaste:* {details.get('aftertaste', '')}"
        )
    return "\n\n".join(sections)


def _runtime_markdown() -> str:
    runtime = _app_metadata()["runtime"]
    validation = _app_metadata()["runtime_validation"]
    lines = [
        f"- Models: `{runtime['model_provider']}`",
        f"- Demo mode: `{runtime['demo_mode']}`",
        f"- Traces: `{runtime['traces_provider']}`",
    ]
    if validation["ok"]:
        lines.append("- Runtime validation: `ok`")
    else:
        lines.extend(f"- Runtime issue: {issue}" for issue in validation["issues"])
    return "\n".join(lines)


def _write_temp_html(html: str | None) -> str | None:
    if not html:
        return None
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    handle.write(html.encode("utf-8"))
    handle.close()
    return handle.name


CUSTOM_CSS = """
:root {
  --ple-paper: #f4ead8;
  --ple-paper-deep: #ead8bc;
  --ple-ink: #1f1713;
  --ple-muted: #5f4e46;
  --ple-rust: #90472f;
  --ple-rust-deep: #6e3523;
  --ple-gold: #d08a22;
  --ple-panel: rgba(255, 250, 243, 0.94);
  --ple-panel-strong: rgba(255, 248, 238, 0.98);
  --ple-line: rgba(107, 71, 44, 0.14);
  --ple-shadow: rgba(31, 20, 17, 0.14);
  --ple-well: #2a2422;
  --ple-well-soft: #3a312e;
}

body, .gradio-container {
  background:
    radial-gradient(circle at top left, rgba(232, 184, 112, 0.34), transparent 28%),
    radial-gradient(circle at top right, rgba(171, 89, 52, 0.16), transparent 22%),
    linear-gradient(180deg, #f7efdf 0%, #f0e1c8 52%, #ead6b8 100%);
  color: var(--ple-ink);
  font-family: Georgia, "Times New Roman", serif !important;
}

.gradio-container {
  max-width: 1380px !important;
  padding: 28px 20px 36px !important;
}

#ple-shell {
  background:
    linear-gradient(180deg, rgba(255,255,255,0.48), rgba(255,255,255,0.2)),
    rgba(248, 239, 225, 0.72);
  border: 1px solid rgba(128, 89, 57, 0.12);
  border-radius: 32px;
  box-shadow: 0 28px 90px var(--ple-shadow);
  overflow: hidden;
}

.ple-hero {
  padding: 56px 54px 36px;
  background:
    radial-gradient(circle at top left, rgba(255, 211, 143, 0.14), transparent 24%),
    linear-gradient(135deg, rgba(62, 31, 20, 0.97), rgba(142, 71, 42, 0.9));
  color: #fff9f0;
}

.ple-kicker {
  text-transform: uppercase;
  letter-spacing: 0.24em;
  font-size: 10px;
  opacity: 0.82;
  margin-bottom: 18px;
}

.ple-hero h1 {
  margin: 0;
  font-size: 64px;
  line-height: 0.92;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.ple-hero p {
  max-width: 760px;
  font-size: 18px;
  line-height: 1.65;
  color: rgba(255, 247, 237, 0.88);
  margin-top: 20px;
}

.ple-band {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.ple-chip {
  padding: 10px 15px;
  border-radius: 999px;
  background: rgba(255, 249, 240, 0.1);
  border: 1px solid rgba(255, 249, 240, 0.18);
  font-size: 12px;
  color: #fff2e5;
}

.ple-section {
  padding: 26px 30px 10px;
}

.ple-card {
  background: var(--ple-panel);
  border: 1px solid var(--ple-line);
  border-radius: 26px;
  box-shadow: 0 18px 48px rgba(72, 41, 27, 0.07);
  backdrop-filter: blur(8px);
}

.ple-subhead {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--ple-rust);
  margin-bottom: 10px;
  font-weight: 700;
}

.ple-title {
  font-size: 40px;
  line-height: 1.02;
  margin: 0 0 12px;
  color: var(--ple-ink);
  letter-spacing: -0.03em;
  font-weight: 700;
}

.ple-blurb {
  color: var(--ple-muted);
  line-height: 1.7;
  margin: 0;
  font-size: 16px;
}

.gr-button-primary {
  background: linear-gradient(135deg, var(--ple-rust-deep), #bf6a38) !important;
  border: none !important;
  color: #fff7f0 !important;
  box-shadow: 0 14px 28px rgba(143, 74, 47, 0.24) !important;
  min-height: 48px !important;
  font-weight: 700 !important;
}

.gr-button-primary:hover {
  filter: brightness(1.05);
}

.gr-button-secondary, .gr-button {
  border-radius: 16px !important;
}

.gr-box, .gr-panel, .gr-form, .gr-group, .gradio-group {
  border-radius: 18px !important;
}

.ple-runtime, .ple-output {
  padding: 26px;
}

.ple-output .prose, .ple-runtime .prose, .ple-card .prose, .ple-card .gr-markdown, .ple-card .gr-markdown *, .ple-card p, .ple-card h1, .ple-card h2, .ple-card h3, .ple-card h4, .ple-card label, .ple-card span, .ple-card textarea, .ple-card input {
  color: var(--ple-ink);
}

.ple-output h1, .ple-output h2, .ple-output h3 {
  color: var(--ple-ink);
}

.ple-card textarea,
.ple-card input,
.ple-card .gr-textbox,
.ple-card .gr-textbox textarea,
.ple-card .gr-textbox input {
  background: rgba(255, 249, 241, 0.96) !important;
  color: var(--ple-ink) !important;
  border: 1px solid rgba(121, 82, 54, 0.16) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
}

.ple-card .gr-textbox textarea::placeholder,
.ple-card .gr-textbox input::placeholder {
  color: rgba(95, 78, 70, 0.72) !important;
}

.ple-card .gradio-image,
.ple-card .gradio-audio,
.ple-card .gr-gallery,
.ple-card .gr-file,
.ple-card .gr-code,
.ple-card .gr-accordion {
  background: transparent !important;
}

.ple-card .image-container,
.ple-card .audio-container,
.ple-card .empty,
.ple-card .wrap,
.ple-card .file-preview,
.ple-card .cm-editor,
.ple-card .cm-scroller,
.ple-card .gallery-container {
  background: var(--ple-well) !important;
  color: #f8efe5 !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
  border-radius: 20px !important;
}

.ple-card .empty,
.ple-card .image-container .placeholder,
.ple-card .audio-container .placeholder {
  color: #f7eee1 !important;
}

.ple-card button,
.ple-card .icon-button {
  border-radius: 14px !important;
}

.ple-card .label-wrap,
.ple-card .block-title,
.ple-card .gallery-header,
.ple-card .accordion-header {
  color: var(--ple-ink) !important;
  font-weight: 700 !important;
}

.ple-card .gallery-item {
  border-radius: 18px !important;
  overflow: hidden;
}

.ple-card .gallery-item img {
  filter: saturate(0.94) contrast(1.02);
}

.ple-card .accordion-header {
  background: var(--ple-well) !important;
  color: #fff4e8 !important;
}

.ple-card .accordion-body {
  background: rgba(248, 242, 234, 0.96) !important;
}

.ple-card .gr-markdown h2 {
  font-size: 28px !important;
  letter-spacing: -0.02em;
}

.ple-card .gr-markdown h3 {
  font-size: 22px !important;
}

.ple-card .gr-markdown p,
.ple-card .gr-markdown li {
  color: var(--ple-ink) !important;
  line-height: 1.72 !important;
  font-size: 15px !important;
}

.ple-card .gr-markdown ul {
  padding-left: 1.1rem !important;
}

.ple-footer-note {
  padding: 6px 34px 34px;
  color: var(--ple-muted);
  font-size: 13px;
}

@media (max-width: 980px) {
  .gradio-container {
    padding: 14px 10px 24px !important;
  }

  .ple-hero {
    padding: 36px 24px 26px;
  }

  .ple-hero h1 {
    font-size: 44px;
  }

  .ple-title {
    font-size: 30px;
  }

  .ple-section {
    padding: 18px 16px 8px;
  }
}
"""


HERO_HTML = """
<section class="ple-hero">
  <div class="ple-kicker">Build Small / Thousand Token Wood / Spectacle-First Memoir Engine</div>
  <h1>Parallel Life Engine</h1>
  <p>
    A machine for mourning the lives you never lived. Start with one portrait and one fork in the road.
    The app reconstructs an alternate memoir across five decades, reveals identity-preserving portraits,
    and packages the result as a keepsake scrapbook.
  </p>
  <div class="ple-band">
    <div class="ple-chip">One portrait</div>
    <div class="ple-chip">One sentence</div>
    <div class="ple-chip">Five decades</div>
    <div class="ple-chip">Progressive reveal</div>
    <div class="ple-chip">Exportable artifact</div>
  </div>
</section>
"""


SPACE_THEME = gr.themes.Soft(
    primary_hue="amber",
    secondary_hue="rose",
    neutral_hue="stone",
) if gr is not None else None


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
            payload.get("log") or "Listening for the next clue.",
            payload.get("life_title") or "The Life Where I Turned",
            payload.get("life_summary") or "A memoir of the choice that kept unfolding.",
            payload.get("transcription") or "",
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
        final_payload.get("log") or "Recovered memoir complete.",
        final_payload.get("life_title") or "The Life Where I Turned",
        final_payload.get("life_summary") or "A memoir of the choice that kept unfolding.",
        final_payload.get("transcription") or "",
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

    with gr.Blocks(title="Parallel Life Engine") as demo:
        gr.HTML(f"<style>{CUSTOM_CSS}</style>")
        with gr.Column(elem_id="ple-shell"):
            gr.HTML(HERO_HTML)

            with gr.Row(elem_classes=["ple-section"]):
                with gr.Column(scale=5, elem_classes=["ple-card"]):
                    gr.HTML(
                        """
                        <div class="ple-section">
                          <div class="ple-subhead">Input Ritual</div>
                          <h2 class="ple-title">Feed the machine one face and one impossible sentence</h2>
                          <p class="ple-blurb">The stronger the fork, the stronger the memoir. Voice and typed text both work.</p>
                        </div>
                        """
                    )
                    photo = gr.Image(type="pil", label="Portrait Photo", height=340)
                    with gr.Row():
                        audio = gr.Audio(type="filepath", label="Voice Fork", sources=["upload", "microphone"])
                        fork_text = gr.Textbox(
                            label="Life Fork",
                            lines=7,
                            placeholder="What if I had moved to Tokyo at 22 and stayed long enough to become a photographer?",
                        )
                    with gr.Row():
                        generate = gr.Button("Reconstruct Life", variant="primary", scale=2)
                        export_file = gr.File(label="Keepsake Export", visible=False, scale=1)
                    gr.Examples(
                        examples=[
                            ["What if I had moved to Tokyo at 22 and stayed long enough to become a photographer?"],
                            ["What if I had joined an indie band in Sao Paulo instead of taking the safe office job?"],
                            ["What if I had accepted the marine biology fellowship and spent my life near the sea?"],
                        ],
                        inputs=[fork_text],
                    )

                with gr.Column(scale=4, elem_classes=["ple-card", "ple-runtime"]):
                    gr.HTML(
                        """
                        <div class="ple-subhead">Runtime</div>
                        <h2 class="ple-title">The reconstruction log</h2>
                        <p class="ple-blurb">This panel updates as the engine moves from fork recovery to memoir, timeline, portraits, and export.</p>
                        """
                    )
                    status = gr.Markdown("Listening for the next clue.")
                    title = gr.Markdown("## The Life Where I Turned")
                    summary = gr.Markdown("A memoir of the choice that kept unfolding.")
                    transcription = gr.Textbox(label="Recovered Fork", interactive=False)
                    runtime = gr.Markdown(_runtime_markdown())
                    errors = gr.Markdown("No visible fractures yet.")

            with gr.Row(elem_classes=["ple-section"]):
                with gr.Column(scale=6, elem_classes=["ple-card", "ple-output"]):
                    gr.HTML(
                        """
                        <div class="ple-subhead">Memoir</div>
                        <h2 class="ple-title">The unlived scrapbook</h2>
                        <p class="ple-blurb">Each decade arrives in first person, with a place, a relationship thread, a defining event, and an emotional aftertaste.</p>
                        """
                    )
                    narrative = gr.Markdown("Your unlived memoir will stream in decade by decade.")
                with gr.Column(scale=4, elem_classes=["ple-card", "ple-output"]):
                    gr.HTML(
                        """
                        <div class="ple-subhead">Portrait Reel</div>
                        <h2 class="ple-title">The face the years might have made</h2>
                        <p class="ple-blurb">Portraits appear progressively as each decade settles into shape.</p>
                        """
                    )
                    gallery = gr.Gallery(label="Decade Portraits", columns=2, height=620, object_fit="cover")

            with gr.Row(elem_classes=["ple-section"]):
                with gr.Column(scale=5, elem_classes=["ple-card", "ple-output"]):
                    gr.HTML(
                        """
                        <div class="ple-subhead">Timeline</div>
                        <h2 class="ple-title">Anchor memories</h2>
                        <p class="ple-blurb">A compact structured timeline for quick judging and replay.</p>
                        """
                    )
                    timeline = gr.Markdown("Timeline notes will appear here.")
                with gr.Column(scale=5, elem_classes=["ple-card", "ple-output"]):
                    gr.HTML(
                        """
                        <div class="ple-subhead">Replay Shelf</div>
                        <h2 class="ple-title">Recovered lives from earlier runs</h2>
                        <p class="ple-blurb">Saved keepsakes stay accessible so the demo still lands even if a live run is slow.</p>
                        """
                    )
                    saved_runs = gr.Markdown(_saved_runs_markdown())

            with gr.Accordion("Raw Streaming Snapshot", open=False, elem_classes=["ple-section"]):
                raw = gr.Code(label="Streaming Snapshot", language="json")

            gr.HTML(
                """
                <div class="ple-footer-note">
                  Build Small note: this submission is intentionally built as a chain of small specialist stages rather than one monolithic response.
                </div>
                """
            )

        generate.click(
            fn=_run_for_gradio,
            inputs=[photo, audio, fork_text],
            outputs=[status, title, summary, transcription, narrative, timeline, gallery, errors, export_file, saved_runs, raw],
        )

    return demo


demo = _build_demo()
app = demo


if __name__ == "__main__" and demo is not None:  # pragma: no cover - runtime entrypoint
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        theme=SPACE_THEME,
    )
