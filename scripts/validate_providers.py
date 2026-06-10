from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def main() -> None:
    image = Image.new("RGB", (96, 96), "#c9b59f")

    vision_model, tokenizer = get_minicpm_v()
    vision_output = json.loads(
        vision_model.chat(image=image, msgs=[{"role": "user", "content": "return json"}], tokenizer=tokenizer)
    )
    validate_vision_payload(vision_output)

    asr_model = get_minicpm_o()
    asr_output = asr_model.transcribe(b"demo-audio")
    validate_asr_payload(asr_output)

    narrative_model, _ = get_narrative_model()
    narrative_output = json.loads(
        narrative_model.generate(system="memoir", prompt='Life fork: "What if I had left?"', max_new_tokens=100, temperature=0.8)
    )
    validate_narrative_payload(narrative_output, DEFAULT_DECADES)

    parser = get_nemotron_parse()
    structure_output = parser.extract(text="demo", schema={"timeline": []})
    validate_structure_payload(structure_output)

    flux = get_flux()
    portrait = flux.generate(prompt="Portrait photo", reference_image=image)
    validate_portrait_object(portrait)

    print("provider-contracts-ok")


if __name__ == "__main__":
    main()
