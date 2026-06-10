from __future__ import annotations

from typing import Any


REQUIRED_VISION_KEYS = {
    "age_estimate",
    "decade_of_photo",
    "visible_context",
    "emotional_tone",
    "geographic_clues",
    "life_stage",
}

REQUIRED_NARRATIVE_KEYS = {
    "narrative",
    "key_event",
    "emotion",
    "location",
    "relationship",
    "physical_memory",
    "aftertaste",
}


def validate_vision_payload(payload: dict[str, Any]) -> None:
    missing = REQUIRED_VISION_KEYS - payload.keys()
    if missing:
        raise ValueError(f"Vision payload missing keys: {sorted(missing)}")
    if not isinstance(payload.get("visible_context"), list) or not payload["visible_context"]:
        raise ValueError("Vision payload must include a non-empty visible_context list")


def validate_asr_payload(payload: dict[str, Any]) -> None:
    if "text" not in payload:
        raise ValueError("ASR payload missing text")
    if "language" not in payload:
        raise ValueError("ASR payload missing language")


def validate_narrative_payload(payload: dict[str, dict[str, Any]], decades: list[str]) -> None:
    missing_decades = [decade for decade in decades if decade not in payload]
    if missing_decades:
        raise ValueError(f"Narrative payload missing decades: {missing_decades}")

    for decade in decades:
        details = payload[decade]
        missing = REQUIRED_NARRATIVE_KEYS - details.keys()
        if missing:
            raise ValueError(f"Narrative payload for {decade} missing keys: {sorted(missing)}")


def validate_structure_payload(payload: dict[str, Any]) -> None:
    timeline = payload.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError("Structure payload must include a non-empty timeline list")


def validate_portrait_object(image: Any) -> None:
    if image is None:
        raise ValueError("Portrait provider returned None")
    if not hasattr(image, "save"):
        raise ValueError("Portrait provider must return a PIL-like image with save()")
