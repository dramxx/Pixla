import logging
import torch
from PIL import Image
from pathlib import Path
from typing import Optional, List
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from app.services.constants import (
    DIFFUSION_TYPE_PROMPTS,
    NEGATIVE_PROMPT,
    RESOLUTION_HINTS,
    RESOLUTION_NEGATIVE_PROMPTS,
)
from app.utils.logging import diffusion_logger, log_operation

logging.getLogger("diffusers").setLevel(logging.ERROR)


class DiffusionService:
    def __init__(
        self,
        model_id: str,
        device: str = "cuda",
        dtype: str = "float16",
    ):
        self.model_id = model_id
        self.device = device
        self.dtype = getattr(torch, dtype, torch.float32)
        self._pipeline: Optional[StableDiffusionPipeline] = None

    def _load_model(self):
        if self._pipeline is not None:
            return

        log_operation(
            diffusion_logger,
            "Loading diffusion model",
            details=f"model={self.model_id}, device={self.device}",
        )

        try:
            model_path = Path(self.model_id)

            if model_path.exists():
                if model_path.suffix in {".safetensors", ".ckpt", ".pt", ".pth"}:
                    self._pipeline = StableDiffusionPipeline.from_single_file(
                        str(model_path),
                        torch_dtype=self.dtype,
                        safety_checker=None,
                        feature_extractor=None,
                    )
                else:
                    self._pipeline = StableDiffusionPipeline.from_pretrained(
                        str(model_path),
                        torch_dtype=self.dtype,
                        safety_checker=None,
                        feature_extractor=None,
                    )
            else:
                raise ValueError(
                    f"Model not found at {self.model_id}. "
                    "Please place model files in storage/models/ folder."
                )

            self._pipeline = self._pipeline.to(self.device)
            self._pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self._pipeline.scheduler.config
            )
            if self.device == "cuda":
                self._pipeline.enable_attention_slicing()
            log_operation(
                diffusion_logger,
                "Diffusion model loaded",
                success=True,
                details=f"model={self.model_id}",
            )
        except Exception as e:
            log_operation(
                diffusion_logger, "Failed to load diffusion model", success=False, error=e
            )
            raise

    def load_loras(self, loras: List[dict]):
        """Load LoRAs into the pipeline with proper scale handling.

        Args:
            loras: List of dicts with 'path' and 'scale' keys
        """
        if not loras or self._pipeline is None:
            return

        self._pipeline.disable_lora()

        adapter_paths = []
        adapter_scales = []

        for lora in loras:
            lora_path = lora.get("path", "")
            scale = lora.get("scale", 1.0)

            if not lora_path:
                continue

            lora_path_obj = Path(lora_path)
            if not lora_path_obj.exists():
                print(f"Warning: LoRA not found at {lora_path}")
                continue

            try:
                self._pipeline.load_lora_weights(
                    str(lora_path_obj),
                    adapter_name=lora_path_obj.stem,
                )
                adapter_paths.append(lora_path_obj.stem)
                adapter_scales.append(scale)
                print(f"Loaded LoRA: {lora_path_obj.name} (scale={scale})")
            except Exception as e:
                print(f"Warning: Failed to load LoRA {lora_path}: {e}")

        if adapter_paths:
            self._pipeline.set_adapters(adapter_paths, adapter_weights=adapter_scales)
            print(f"Applied LoRA scales: {dict(zip(adapter_paths, adapter_scales))}")

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        self._load_model()

        log_operation(
            diffusion_logger,
            "Generating image",
            details=f"prompt={prompt[:50]}..., size={width}x{height}, steps={num_inference_steps}",
        )

        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None

        result = self._pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )

        log_operation(
            diffusion_logger, "Image generated", success=True, details=f"size={width}x{height}"
        )
        return result.images[0]

    def generate_pixel_art_reference(
        self,
        prompt: str,
        sprite_type: str = "block",
        target_size: int = 512,
        loras: Optional[List[dict]] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        # Backwards compatibility alias
        size: Optional[int] = None,
    ) -> Image.Image:
        # Support legacy 'size' parameter
        if size is not None:
            target_size = size
        self._load_model()

        if loras:
            self.load_loras(loras)

        enhanced_prompt = (
            f"{prompt}. {DIFFUSION_TYPE_PROMPTS.get(sprite_type, DIFFUSION_TYPE_PROMPTS['block'])}"
        )

        # Add resolution-specific hints
        res_hint = RESOLUTION_HINTS.get(target_size, "")
        if res_hint:
            enhanced_prompt = f"{enhanced_prompt}. {res_hint}"

        steps = num_inference_steps if num_inference_steps is not None else 25
        guidance = guidance_scale if guidance_scale is not None else 8.0

        # Build negative prompt with resolution-specific additions
        negative_prompt = NEGATIVE_PROMPT
        res_negative = RESOLUTION_NEGATIVE_PROMPTS.get(target_size, "")
        if res_negative:
            negative_prompt = f"{negative_prompt}, {res_negative}"

        return self.generate(
            prompt=enhanced_prompt,
            negative_prompt=negative_prompt,
            width=target_size,
            height=target_size,
            num_inference_steps=steps,
            guidance_scale=guidance,
        )

    def unload(self):
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            if self.device == "cuda":
                torch.cuda.empty_cache()


_diffusion_instance: Optional[DiffusionService] = None


def get_diffusion(model_id: Optional[str] = None) -> DiffusionService:
    global _diffusion_instance

    effective_model_id = model_id
    if effective_model_id is None:
        from app.config import get_settings

        settings = get_settings()
        effective_model_id = settings.model_id

    if effective_model_id is None:
        raise ValueError(
            "No model specified. Set MODEL_ID in .env or select a model from storage/models"
        )

    if _diffusion_instance is None:
        from app.config import get_settings

        settings = get_settings()
        _diffusion_instance = DiffusionService(
            model_id=effective_model_id,
            device=settings.model_device,
            dtype=settings.model_dtype,
        )
    if _diffusion_instance.model_id != effective_model_id:
        _diffusion_instance.unload()
        _diffusion_instance = DiffusionService(
            model_id=effective_model_id,
            device=_diffusion_instance.device,
            dtype=str(_diffusion_instance.dtype).replace("torch.", ""),
        )
    return _diffusion_instance


def unload_diffusion():
    global _diffusion_instance
    if _diffusion_instance is not None:
        _diffusion_instance.unload()
        _diffusion_instance = None
