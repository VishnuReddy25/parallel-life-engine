from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from pipeline.orchestrator import LifeState


async def step_export(state: LifeState) -> LifeState:
    if not state.life_arc:
        return state

    template_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    template = template_path.read_text(encoding="utf-8")

    pages = []
    for decade, data in state.life_arc.items():
        portrait = state.portraits.get(decade)
        image_b64 = ""
        if portrait:
            buffer = io.BytesIO()
            portrait.save(buffer, format="JPEG", quality=88)
            image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        pages.append(
            {
                "decade": decade,
                "narrative": data["narrative"],
                "key_event": data["key_event"],
                "emotion": data["emotion"],
                "location": data["location"],
                "relationship": data["relationship"],
                "physical_memory": data["physical_memory"],
                "aftertaste": data["aftertaste"],
                "portrait_b64": image_b64,
            }
        )

    payload = {
        "title": state.life_title or "The Life Where I Turned",
        "summary": state.life_summary or "A memoir of the choice that kept unfolding.",
        "transcription": state.transcription,
        "language_detected": state.language_detected,
        "trace_id": state.trace_id,
        "trace_path": state.trace_path,
        "export_path": state.export_path,
        "pages": pages,
        "timeline": state.timeline or [],
        "portrait_failures": state.portrait_failures,
    }
    state.scrapbook_html = template.replace("{{PAGES_DATA}}", json.dumps(payload))
    state.export_ready = True
    return state
