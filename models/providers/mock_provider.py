from __future__ import annotations

import json

from PIL import Image, ImageDraw

from pipeline.orchestrator import DEFAULT_DECADES


class MockMiniCPMV:
    def chat(self, image, msgs, tokenizer=None):  # noqa: ANN001
        prompt = msgs[0]["content"] if msgs else ""
        if "invalid_json" in prompt:
            return "{"

        return json.dumps(
            {
                "age_estimate": 28,
                "decade_of_photo": "2010s",
                "visible_context": [
                    "soft window light",
                    "plain wall",
                    "calm posture",
                    "casual shirt",
                    "close portrait crop",
                ],
                "emotional_tone": "hopeful",
                "geographic_clues": "urban contemporary portrait styling",
                "life_stage": "young_adult",
            }
        )


class MockMiniCPMO:
    def transcribe(self, _audio: bytes) -> dict[str, object]:
        return {
            "text": "What if I had stayed where the train line ended?",
            "language": "en",
            "confidence": 0.92,
        }


class MockNarrativeModel:
    def generate(self, system: str, prompt: str, max_new_tokens: int, temperature: float) -> str:  # noqa: ARG002
        if "FORCE_INVALID_NARRATIVE" in prompt:
            return "not json"

        fork = "a different life"
        if 'Life fork: "' in prompt:
            fork = prompt.split('Life fork: "', 1)[1].split('"', 1)[0]

        arc = {}
        for index, decade in enumerate(DEFAULT_DECADES):
            age = 20 + (index * 10)
            arc[decade] = {
                "narrative": (
                    f"In my {decade}, {fork.lower()} became the quiet engine of everything. "
                    f"I was {age}-something and kept returning to the same streetlamp-lit hour, "
                    "remembering a relationship that changed shape when I finally chose motion over safety. "
                    "There was always a place I could smell before I saw it, and every victory arrived with a bruise of doubt."
                ),
                "key_event": f"A defining turning point in my {decade}",
                "emotion": ["yearning", "awe", "restlessness", "tenderness", "acceptance"][index],
                "location": ["Osaka", "Seoul", "Berlin", "Valparaiso", "Mysuru"][index],
                "relationship": [
                    "a roommate who became family",
                    "a love I almost missed",
                    "a child learning my old silences",
                    "a parent I finally understood",
                    "a friend who stayed until the last chapter",
                ][index],
                "physical_memory": [
                    "rain in my shoes",
                    "paint on my wrists",
                    "metal handrails gone warm in summer",
                    "the ache behind my eyes after overnight work",
                    "cardamom steam on cold mornings",
                ][index],
                "aftertaste": ["wonder", "homesickness", "ambition", "grief", "mercy"][index],
            }
        return json.dumps(arc)


class MockNemotronParser:
    def extract(self, text: str, schema: dict) -> dict[str, list[dict[str, object]]]:  # noqa: ARG002
        timeline = []
        for index, decade in enumerate(DEFAULT_DECADES):
            timeline.append(
                {
                    "decade": decade,
                    "year_approx": 2000 + (index * 10),
                    "event": f"Anchor memory parsed from {decade}",
                    "location": ["Osaka", "Seoul", "Berlin", "Valparaiso", "Mysuru"][index],
                    "relationship": f"Relationship thread for {decade}",
                    "emotion": ["yearning", "awe", "restlessness", "tenderness", "acceptance"][index],
                }
            )
        return {"timeline": timeline}


class MockFluxPipeline:
    def generate(
        self,
        prompt: str,
        reference_image=None,  # noqa: ANN001
        reference_strength: float = 0.55,  # noqa: ARG002
        num_inference_steps: int = 28,  # noqa: ARG002
        guidance_scale: float = 7.0,  # noqa: ARG002
    ) -> Image.Image:
        if "FAIL_PORTRAIT" in prompt:
            raise RuntimeError("portrait render failed")

        base = reference_image.copy().convert("RGB") if reference_image else Image.new("RGB", (768, 960), "#c9b59f")
        image = base.resize((768, 960))
        overlay = Image.new("RGBA", image.size, (114, 59, 41, 62))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(image)
        draw.rectangle((36, 36, 732, 924), outline="#f7eadf", width=6)
        draw.text((72, 72), prompt[:120], fill="#fff7f0")
        return image


def get_minicpm_v():
    return MockMiniCPMV(), object()


def get_minicpm_o():
    return MockMiniCPMO()


def get_narrative_model():
    return MockNarrativeModel(), object()


def get_nemotron_parse():
    return MockNemotronParser()


def get_flux():
    return MockFluxPipeline()
