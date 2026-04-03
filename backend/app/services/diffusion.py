import torch
from PIL import Image
from typing import Optional
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from app.services.constants import DIFFUSION_TYPE_PROMPTS, NEGATIVE_PROMPT


class DiffusionService:
    def __init__(
        self,
        model_id: str = "runwayml/stable-diffusion-v1-5",
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

        print(f"Loading model {self.model_id} on {self.device}...")

        try:
            self._pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
            )
            self._pipeline = self._pipeline.to(self.device)
            self._pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self._pipeline.scheduler.config
            )
            if self.device == "cuda":
                self._pipeline.enable_attention_slicing()
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

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

        return result.images[0]

    def generate_pixel_art_reference(
        self,
        prompt: str,
        sprite_type: str = "block",
        size: int = 512,
    ) -> Image.Image:
        enhanced_prompt = (
            f"{prompt}. {DIFFUSION_TYPE_PROMPTS.get(sprite_type, DIFFUSION_TYPE_PROMPTS['block'])}"
        )

        return self.generate(
            prompt=enhanced_prompt,
            negative_prompt=NEGATIVE_PROMPT,
            width=size,
            height=size,
            num_inference_steps=25,
            guidance_scale=8.0,
        )

    def unload(self):
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            if self.device == "cuda":
                torch.cuda.empty_cache()


_diffusion_instance: Optional[DiffusionService] = None


def get_diffusion() -> DiffusionService:
    global _diffusion_instance
    if _diffusion_instance is None:
        from app.config import get_settings

        settings = get_settings()
        _diffusion_instance = DiffusionService(
            model_id=settings.model_id,
            device=settings.model_device,
            dtype=settings.model_dtype,
        )
    return _diffusion_instance


def unload_diffusion():
    global _diffusion_instance
    if _diffusion_instance is not None:
        _diffusion_instance.unload()
        _diffusion_instance = None
