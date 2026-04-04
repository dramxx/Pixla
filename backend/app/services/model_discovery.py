"""Model discovery service - scans folders for available models and LoRAs."""

import json
from pathlib import Path
from typing import Optional
from app.models.config import ModelConfig, LoRAConfig


class ModelDiscovery:
    """Discovers models and LoRAs from storage folders."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.models_dir = self.storage_path / "models"
        self.loras_dir = self.storage_path / "loras"

    def _ensure_dirs(self):
        """Create directories if they don't exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.loras_dir.mkdir(parents=True, exist_ok=True)

    def list_models(self) -> list[ModelConfig]:
        """List all available models by scanning models directory."""
        self._ensure_dirs()
        models = []

        model_extensions = {".safetensors", ".ckpt", ".pt", ".pth"}

        for model_path in self.models_dir.iterdir():
            if model_path.is_dir():
                # Check for config.json in subdirectory
                config_path = model_path / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            config_data = json.load(f)
                            config = ModelConfig(**config_data)
                            config.path = str(model_path)
                            models.append(config)
                    except Exception as e:
                        print(f"Warning: Failed to load config for {model_path}: {e}")
                        continue

                # If no config, create basic entry from folder name
                model_id = model_path.name
                config = ModelConfig(
                    id=model_id,
                    name=model_id.replace("-", " ").replace("_", " ").title(),
                    source="local",
                    path=str(model_path),
                    is_default=False,
                )
                models.append(config)
            elif model_path.is_file() and model_path.suffix.lower() in model_extensions:
                # Handle direct model files
                model_id = model_path.stem
                config = ModelConfig(
                    id=model_id,
                    name=model_id.replace("-", " ").replace("_", " ").title(),
                    source="local",
                    path=str(model_path),
                    is_default=False,
                )
                models.append(config)

        return models

    def list_loras(self) -> list[LoRAConfig]:
        """List all available LoRAs by scanning loras directory."""
        self._ensure_dirs()
        loras = []

        lora_extensions = {".safetensors", ".ckpt", ".pt", ".pth", ".bin"}

        for lora_path in self.loras_dir.iterdir():
            if lora_path.is_dir():
                # Check for config.json
                config_path = lora_path / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            config_data = json.load(f)
                            config = LoRAConfig(**config_data)
                            config.path = str(lora_path)
                            loras.append(config)
                    except Exception as e:
                        print(f"Warning: Failed to load config for {lora_path}: {e}")
                        continue

                # If no config, create basic entry
                lora_id = lora_path.name
                config = LoRAConfig(
                    id=lora_id,
                    name=lora_id.replace("-", " ").replace("_", " ").title(),
                    path=str(lora_path),
                    enabled=True,
                )
                loras.append(config)
            elif lora_path.is_file() and lora_path.suffix.lower() in lora_extensions:
                # Handle direct LoRA files
                lora_id = lora_path.stem
                config = LoRAConfig(
                    id=lora_id,
                    name=lora_id.replace("-", " ").replace("_", " ").title(),
                    path=str(lora_path),
                    enabled=True,
                )
                loras.append(config)

        return loras

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a specific model by ID."""
        models = self.list_models()
        for model in models:
            if model.id == model_id:
                return model
        return None

    def get_lora(self, lora_id: str) -> Optional[LoRAConfig]:
        """Get a specific LoRA by ID."""
        loras = self.list_loras()
        for lora in loras:
            if lora.id == lora_id:
                return lora
        return None


# Singleton instance
_discovery_instance: Optional[ModelDiscovery] = None


def get_model_discovery(storage_path: str = "./storage") -> ModelDiscovery:
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ModelDiscovery(storage_path)
    elif str(_discovery_instance.storage_path) != storage_path:
        _discovery_instance = ModelDiscovery(storage_path)
    return _discovery_instance


def reset_model_discovery():
    """Reset the singleton - useful for testing or reconfiguring storage path."""
    global _discovery_instance
    _discovery_instance = None
