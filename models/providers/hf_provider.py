from __future__ import annotations

import gc
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps

from settings import SETTINGS


def get_provider_metadata() -> dict[str, object]:
    configured_env = {
        "HF_TOKEN": bool(SETTINGS.hf_token),
        "PLE_HF_SPACE_ID": bool(SETTINGS.hf_space_id),
    }
    return {
        "implemented": True,
        "provider_key": "hf",
        "mode": "local_space_gpu",
        "requires_env": [],
        "recommended_env": ["HF_TOKEN", "PLE_HF_SPACE_ID"],
        "configured_env": configured_env,
        "missing_env": [],
        "stack": {
            "vision": SETTINGS.hf_vision_model,
            "asr": SETTINGS.hf_asr_model,
            "narrative": SETTINGS.hf_narrative_model,
            "structure": SETTINGS.hf_structure_model,
            "portraits": SETTINGS.hf_portrait_model,
        },
        "runtime": {
            "device": SETTINGS.hf_device,
            "dtype": SETTINGS.hf_dtype,
            "offload_between_steps": SETTINGS.hf_offload_between_steps,
            "low_cpu_mem_usage": SETTINGS.hf_low_cpu_mem_usage,
        },
        "notes": (
            "Runs models inside the Hugging Face Space process. No inference API calls. "
            "Models are loaded lazily and unloaded between stages to fit a single-GPU Space."
        ),
    }


def _lazy_import_torch():
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "HF local mode requires 'torch'. Add the Space GPU dependencies from requirements.txt."
        ) from exc
    return torch


def _lazy_import_transformers():
    try:
        import transformers
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "HF local mode requires 'transformers'. Add the Space GPU dependencies from requirements.txt."
        ) from exc
    return transformers


def _lazy_import_diffusers():
    try:
        import diffusers
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "HF local mode requires 'diffusers'. Add the Space GPU dependencies from requirements.txt."
        ) from exc
    return diffusers


def _resolve_device() -> str:
    if SETTINGS.hf_device != "auto":
        return SETTINGS.hf_device
    torch = _lazy_import_torch()
    return "cuda" if torch.cuda.is_available() else "cpu"


def _resolve_torch_dtype():
    torch = _lazy_import_torch()
    if SETTINGS.hf_dtype == "float16":
        return torch.float16
    if SETTINGS.hf_dtype == "bfloat16":
        return torch.bfloat16
    if SETTINGS.hf_dtype == "float32":
        return torch.float32

    device = _resolve_device()
    if device == "cuda":
        return torch.bfloat16 if getattr(torch.cuda, "is_bf16_supported", lambda: False)() else torch.float16
    return torch.float32


@dataclass
class LoadedArtifact:
    task: str
    model: Any
    aux: Any = None


class LocalModelRuntime:
    def __init__(self):
        self._loaded: LoadedArtifact | None = None
        self._device: str | None = None
        self._dtype = None

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = _resolve_device()
        return self._device

    @property
    def dtype(self):
        if self._dtype is None:
            self._dtype = _resolve_torch_dtype()
        return self._dtype

    def activate(self, task: str) -> LoadedArtifact:
        if self._loaded and self._loaded.task == task:
            return self._loaded

        self.unload()
        loader = getattr(self, f"_load_{task}")
        self._loaded = loader()
        return self._loaded

    def unload(self) -> None:
        self._loaded = None
        gc.collect()
        try:
            torch = _lazy_import_torch()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except RuntimeError:
            return

    def _model_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"low_cpu_mem_usage": SETTINGS.hf_low_cpu_mem_usage}
        if self.device == "cuda":
            kwargs["torch_dtype"] = self.dtype
        return kwargs

    def _load_vision(self) -> LoadedArtifact:
        transformers = _lazy_import_transformers()
        processor = transformers.AutoProcessor.from_pretrained(SETTINGS.hf_vision_model, token=SETTINGS.hf_token)
        model = _load_with_fallback(
            primary=lambda: transformers.AutoModelForImageTextToText.from_pretrained(
                SETTINGS.hf_vision_model,
                token=SETTINGS.hf_token,
                **self._model_kwargs(),
            ),
            fallback=lambda: transformers.AutoModelForVision2Seq.from_pretrained(
                SETTINGS.hf_vision_model,
                token=SETTINGS.hf_token,
                **self._model_kwargs(),
            ),
            label="vision model",
        )
        _move_to_device(model, self.device)
        return LoadedArtifact(task="vision", model=model, aux=processor)

    def _load_asr(self) -> LoadedArtifact:
        transformers = _lazy_import_transformers()
        pipeline = transformers.pipeline(
            task="automatic-speech-recognition",
            model=SETTINGS.hf_asr_model,
            token=SETTINGS.hf_token,
            device=0 if self.device == "cuda" else -1,
            torch_dtype=self.dtype if self.device == "cuda" else None,
        )
        return LoadedArtifact(task="asr", model=pipeline)

    def _load_narrative(self) -> LoadedArtifact:
        transformers = _lazy_import_transformers()
        tokenizer = transformers.AutoTokenizer.from_pretrained(SETTINGS.hf_narrative_model, token=SETTINGS.hf_token)
        model = transformers.AutoModelForCausalLM.from_pretrained(
            SETTINGS.hf_narrative_model,
            token=SETTINGS.hf_token,
            **self._model_kwargs(),
        )
        _move_to_device(model, self.device)
        return LoadedArtifact(task="narrative", model=model, aux=tokenizer)

    def _load_structure(self) -> LoadedArtifact:
        transformers = _lazy_import_transformers()
        tokenizer = transformers.AutoTokenizer.from_pretrained(SETTINGS.hf_structure_model, token=SETTINGS.hf_token)
        model = transformers.AutoModelForCausalLM.from_pretrained(
            SETTINGS.hf_structure_model,
            token=SETTINGS.hf_token,
            **self._model_kwargs(),
        )
        _move_to_device(model, self.device)
        return LoadedArtifact(task="structure", model=model, aux=tokenizer)

    def _load_portraits(self) -> LoadedArtifact:
        diffusers = _lazy_import_diffusers()
        pipeline = _load_with_fallback(
            primary=lambda: diffusers.AutoPipelineForImage2Image.from_pretrained(
                SETTINGS.hf_portrait_model,
                token=SETTINGS.hf_token,
                **self._model_kwargs(),
            ),
            fallback=lambda: diffusers.DiffusionPipeline.from_pretrained(
                SETTINGS.hf_portrait_model,
                token=SETTINGS.hf_token,
                **self._model_kwargs(),
            ),
            label="portrait pipeline",
        )
        _move_to_device(pipeline, self.device)
        if hasattr(pipeline, "set_progress_bar_config"):
            pipeline.set_progress_bar_config(disable=True)
        return LoadedArtifact(task="portraits", model=pipeline)


def _load_with_fallback(primary, fallback, label: str):
    try:
        return primary()
    except Exception as primary_error:  # pragma: no cover - library/model specific
        try:
            return fallback()
        except Exception as fallback_error:  # pragma: no cover - library/model specific
            raise RuntimeError(
                f"Could not load {label}. Primary error: {primary_error}. Fallback error: {fallback_error}."
            ) from fallback_error


def _move_to_device(model: Any, device: str) -> None:
    if hasattr(model, "to"):
        model.to(device)


RUNTIME = LocalModelRuntime()


def _maybe_offload() -> None:
    if SETTINGS.hf_offload_between_steps:
        RUNTIME.unload()


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _decode_generated_text(output: Any, tokenizer: Any, prompt_length: int = 0) -> str:
    if isinstance(output, str):
        return output
    if hasattr(output, "sequences"):
        output = output.sequences
    if isinstance(output, (list, tuple)) and output:
        output = output[0]
    if hasattr(output, "tolist"):
        decoded = tokenizer.decode(output[prompt_length:], skip_special_tokens=True)
        return decoded
    raise RuntimeError("Could not decode model output into text.")


class HFMiniCPMV:
    def chat(self, image, msgs, tokenizer=None):  # noqa: ANN001, ARG002
        loaded = RUNTIME.activate("vision")
        processor = loaded.aux
        model = loaded.model
        prompt = msgs[0]["content"] if msgs else "Return valid JSON."

        if hasattr(processor, "apply_chat_template"):
            conversation = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image"}]}]
            formatted = processor.apply_chat_template(conversation, add_generation_prompt=True)
            inputs = processor(text=formatted, images=[image], return_tensors="pt")
        else:
            inputs = processor(text=prompt, images=image, return_tensors="pt")

        inputs = _to_device(inputs, RUNTIME.device)
        output = model.generate(**inputs, max_new_tokens=500)
        text = _decode_generated_text(output, processor if hasattr(processor, "decode") else loaded.aux, 0)
        _maybe_offload()
        return _extract_json_object(text)


class HFASRModel:
    def transcribe(self, audio: bytes) -> dict[str, object]:
        if not audio:
            raise RuntimeError("ASR requested without audio bytes.")

        loaded = RUNTIME.activate("asr")
        suffix = os.getenv("PLE_AUDIO_SUFFIX", ".webm")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(audio)
            temp_path = handle.name

        try:
            result = loaded.model(temp_path)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            _maybe_offload()

        if not isinstance(result, dict):
            raise RuntimeError("ASR pipeline returned an unexpected response.")
        return {
            "text": result.get("text") or "",
            "language": result.get("language") or "en",
            "confidence": result.get("confidence", 0.9),
        }


class _LocalCausalModel:
    task_name = "narrative"

    def _generate(self, system: str, prompt: str, max_new_tokens: int, temperature: float) -> str:
        loaded = RUNTIME.activate(self.task_name)
        model = loaded.model
        tokenizer = loaded.aux
        merged_prompt = f"<system>\n{system.strip()}\n</system>\n<user>\n{prompt.strip()}\n</user>\n<assistant>\n"
        inputs = tokenizer(merged_prompt, return_tensors="pt")
        inputs = _to_device(inputs, RUNTIME.device)
        prompt_length = inputs["input_ids"].shape[-1]
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=max(temperature, 0.1),
            pad_token_id=getattr(tokenizer, "eos_token_id", None),
        )
        text = _decode_generated_text(output, tokenizer, prompt_length)
        _maybe_offload()
        return _extract_json_object(text)


class HFNarrativeModel(_LocalCausalModel):
    task_name = "narrative"

    def generate(self, system: str, prompt: str, max_new_tokens: int, temperature: float) -> str:
        return self._generate(system, prompt, max_new_tokens, temperature)


class HFNemotronParser(_LocalCausalModel):
    task_name = "structure"

    def extract(self, text: str, schema: dict) -> dict[str, list[dict[str, object]]]:
        prompt = (
            "Extract a timeline from the memoir text below. Return only valid JSON with a top-level 'timeline' key. "
            "Each row must include decade, year_approx, event, location, relationship, and emotion.\n\n"
            f"Expected shape:\n{json.dumps(schema)}\n\nMemoir:\n{text}"
        )
        raw = self._generate("You convert memoir prose into compact structured timelines.", prompt, 700, 0.1)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("timeline"), list):
            raise RuntimeError("Structure model did not return a timeline list.")
        return parsed


class HFFluxPipeline:
    def generate(
        self,
        prompt: str,
        reference_image=None,  # noqa: ANN001
        reference_strength: float = 0.55,
        num_inference_steps: int = 28,
        guidance_scale: float = 7.0,
    ) -> Image.Image:
        loaded = RUNTIME.activate("portraits")
        pipeline = loaded.model

        if reference_image is not None:
            try:
                result = pipeline(
                    prompt=prompt,
                    image=reference_image,
                    strength=max(min(reference_strength, 0.95), 0.15),
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps,
                )
            except TypeError:
                result = pipeline(
                    prompt=prompt,
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps,
                )
        else:
            result = pipeline(
                prompt=prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
            )

        image = _extract_first_image(result)
        _maybe_offload()
        return ImageOps.exif_transpose(image.convert("RGB"))


def _extract_first_image(result: Any) -> Image.Image:
    images = getattr(result, "images", None)
    if images and isinstance(images, list):
        return images[0]
    if isinstance(result, Image.Image):
        return result
    raise RuntimeError("Portrait pipeline did not produce an image.")


def _to_device(inputs: Any, device: str):
    if hasattr(inputs, "to"):
        return inputs.to(device)
    if isinstance(inputs, dict):
        converted = {}
        for key, value in inputs.items():
            converted[key] = value.to(device) if hasattr(value, "to") else value
        return converted
    return inputs


def get_minicpm_v():
    return HFMiniCPMV(), object()


def get_minicpm_o():
    return HFASRModel()


def get_narrative_model():
    return HFNarrativeModel(), object()


def get_nemotron_parse():
    return HFNemotronParser()


def get_flux():
    return HFFluxPipeline()
