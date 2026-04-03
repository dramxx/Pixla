"""Model discovery API endpoints."""

from fastapi import APIRouter, Request
from typing import List

from app.models.config import ModelConfig, LoRAConfig
from app.services.model_discovery import get_model_discovery

router = APIRouter()


@router.get("/models", response_model=List[ModelConfig])
async def list_models(request: Request):
    """List all available models (from storage/models folder)."""
    discovery = get_model_discovery(request.app.state.storage_path)
    return discovery.list_models()


@router.get("/models/{model_id}", response_model=ModelConfig)
async def get_model(model_id: str, request: Request):
    """Get a specific model by ID."""
    discovery = get_model_discovery(request.app.state.storage_path)
    model = discovery.get_model(model_id)
    if model is None:
        from fastapi import HTTPException

        raise HTTPException(404, f"Model '{model_id}' not found")
    return model


@router.get("/models/default", response_model=ModelConfig)
async def get_default_model(request: Request):
    """Get the default model."""
    discovery = get_model_discovery(request.app.state.storage_path)
    return discovery.get_default_model()


@router.get("/loras", response_model=List[LoRAConfig])
async def list_loras(request: Request):
    """List all available LoRAs (from storage/loras folder)."""
    discovery = get_model_discovery(request.app.state.storage_path)
    return discovery.list_loras()


@router.get("/loras/{lora_id}", response_model=LoRAConfig)
async def get_lora(lora_id: str, request: Request):
    """Get a specific LoRA by ID."""
    discovery = get_model_discovery(request.app.state.storage_path)
    lora = discovery.get_lora(lora_id)
    if lora is None:
        from fastapi import HTTPException

        raise HTTPException(404, f"LoRA '{lora_id}' not found")
    return lora


@router.get("/settings")
async def get_settings(request: Request):
    """Get application settings including available models, sprite types, etc."""
    from app.config import get_settings

    settings = get_settings()
    discovery = get_model_discovery(request.app.state.storage_path)

    return {
        "system_prompt": settings.system_prompt or "",
        "models": discovery.list_models(),
        "loras": discovery.list_loras(),
        "default_model": settings.model_id,
        "sprite_types": {
            "block": {"label": "Block (Tile)", "has_tileset": True},
            "icon": {"label": "Item Icon", "has_tileset": False},
            "entity": {"label": "Character Sprite", "has_tileset": False},
            "autotile": {"label": "Autotile", "has_tileset": True},
        },
        "config": {
            "reference_size": settings.reference_size,
            "max_iterations": settings.max_iterations,
            "llm_timeout": settings.llm_timeout,
        },
    }
