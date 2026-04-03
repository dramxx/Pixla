import pytest
import tempfile
import os
import json
from pathlib import Path
from app.services.model_discovery import ModelDiscovery


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestModelDiscovery:
    def test_list_models_empty(self, temp_storage):
        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        # Should return default model when no models found
        assert len(models) >= 1
        assert any(m.id == "default" for m in models)

    def test_list_models_with_config(self, temp_storage):
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "my-model"
        model_dir.mkdir()

        config = {
            "id": "my-model",
            "name": "My Custom Model",
            "source": "local",
            "path": str(model_dir),
            "is_default": True,
        }
        with open(model_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "my-model")
        assert model.name == "My Custom Model"
        assert model.source == "local"
        assert model.is_default == True

    def test_list_models_without_config(self, temp_storage):
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "another-model"
        model_dir.mkdir()

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "another-model")
        assert model.name == "Another Model"  # Auto-formatted
        assert model.source == "local"

    def test_list_loras_empty(self, temp_storage):
        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        assert loras == []

    def test_list_loras_with_config(self, temp_storage):
        loras_dir = Path(temp_storage) / "loras"
        loras_dir.mkdir(parents=True)

        lora_dir = loras_dir / "my-lora"
        lora_dir.mkdir()

        config = {
            "id": "my-lora",
            "name": "My LoRA",
            "path": str(lora_dir),
        }
        with open(lora_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        lora = next(l for l in loras if l.id == "my-lora")
        assert lora.name == "My LoRA"
        assert lora.enabled == True  # Default

    def test_list_loras_without_config(self, temp_storage):
        loras_dir = Path(temp_storage) / "loras"
        loras_dir.mkdir(parents=True)

        lora_dir = loras_dir / "test-lora"
        lora_dir.mkdir()

        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        lora = next(l for l in loras if l.id == "test-lora")
        assert lora.name == "Test Lora"
        assert lora.enabled == True

    def test_get_model(self, temp_storage):
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "specific-model"
        model_dir.mkdir()

        config = {
            "id": "specific-model",
            "name": "Specific",
            "source": "local",
            "path": str(model_dir),
        }
        with open(model_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        model = discovery.get_model("specific-model")

        assert model is not None
        assert model.name == "Specific"

    def test_get_model_not_found(self, temp_storage):
        discovery = ModelDiscovery(temp_storage)
        model = discovery.get_model("nonexistent")

        assert model is None

    def test_get_lora(self, temp_storage):
        loras_dir = Path(temp_storage) / "loras"
        loras_dir.mkdir(parents=True)

        lora_dir = loras_dir / "my-lora"
        lora_dir.mkdir()

        config = {"id": "my-lora", "name": "My LoRA", "path": str(lora_dir)}
        with open(lora_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        lora = discovery.get_lora("my-lora")

        assert lora is not None
        assert lora.name == "My LoRA"

    def test_get_default_model(self, temp_storage):
        discovery = ModelDiscovery(temp_storage)
        model = discovery.get_default_model()

        assert model is not None
        assert model.id == "default"

    def test_get_default_model_with_custom(self, temp_storage):
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "custom-model"
        model_dir.mkdir()

        config = {
            "id": "custom-model",
            "name": "Custom",
            "source": "local",
            "path": str(model_dir),
            "is_default": True,
        }
        with open(model_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        model = discovery.get_default_model()

        assert model.id == "custom-model"

    def test_ensure_dirs_creates_directories(self, temp_storage):
        discovery = ModelDiscovery(temp_storage)
        discovery._ensure_dirs()

        assert (Path(temp_storage) / "models").exists()
        assert (Path(temp_storage) / "loras").exists()
