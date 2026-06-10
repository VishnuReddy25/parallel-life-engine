import json

from PIL import Image

from models.load_flux import get_flux
from models.load_minicpm_o import get_minicpm_o
from models.load_minicpm_v import get_minicpm_v
from models.load_narrative_lora import get_narrative_model
from models.load_nemotron_parse import get_nemotron_parse
from models.provider_contracts import (
    validate_asr_payload,
    validate_narrative_payload,
    validate_portrait_object,
    validate_structure_payload,
    validate_vision_payload,
)
from pipeline.orchestrator import DEFAULT_DECADES


def test_mock_provider_contracts_hold():
    image = Image.new("RGB", (64, 64), "#c9b59f")

    vision_model, tokenizer = get_minicpm_v()
    vision_payload = json.loads(
        vision_model.chat(image=image, msgs=[{"role": "user", "content": "return json"}], tokenizer=tokenizer)
    )
    validate_vision_payload(vision_payload)

    asr_payload = get_minicpm_o().transcribe(b"audio")
    validate_asr_payload(asr_payload)

    narrative_model, _ = get_narrative_model()
    narrative_payload = json.loads(
        narrative_model.generate(system="memoir", prompt='Life fork: "What if I had left?"', max_new_tokens=100, temperature=0.8)
    )
    validate_narrative_payload(narrative_payload, DEFAULT_DECADES)

    structure_payload = get_nemotron_parse().extract(text="demo", schema={"timeline": []})
    validate_structure_payload(structure_payload)

    portrait = get_flux().generate(prompt="Portrait photo", reference_image=image)
    validate_portrait_object(portrait)
