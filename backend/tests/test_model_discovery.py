import pytest
import tempfile
import json
from pathlib import Path
from app.services.model_discovery import ModelDiscovery


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestModelDiscovery:
    def test_list_models_empty(self, temp_storage):
        """No models should return empty list (no fallback)."""
        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        assert models == []

    def test_list_models_with_config(self, temp_storage):
        """Model in subdirectory with config.json should be detected."""
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "my-model"
        model_dir.mkdir()

        config = {
            "id": "my-model",
            "name": "My Custom Model",
            "source": "local",
            "path": str(model_dir),
        }
        with open(model_dir / "config.json", "w") as f:
            json.dump(config, f)

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "my-model")
        assert model.name == "My Custom Model"
        assert model.source == "local"

    def test_list_models_without_config(self, temp_storage):
        """Model in subdirectory without config should auto-generate name."""
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        model_dir = models_dir / "another-model"
        model_dir.mkdir()

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "another-model")
        assert model.name == "Another Model"
        assert model.source == "local"

    def test_list_models_safetensors_file(self, temp_storage):
        """Direct .safetensors file should be detected as model."""
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        # Create dummy safetensors file
        safetensors_file = models_dir / "pixel_model.safetensors"
        safetensors_file.write_bytes(b"dummy model data")

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "pixel_model")
        assert model.name == "Pixel Model"
        assert model.source == "local"
        assert "pixel_model.safetensors" in model.path

    def test_list_models_ckpt_file(self, temp_storage):
        """Direct .ckpt file should be detected as model."""
        models_dir = Path(temp_storage) / "models"
        models_dir.mkdir(parents=True)

        ckpt_file = models_dir / "test_model.ckpt"
        ckpt_file.write_bytes(b"dummy model data")

        discovery = ModelDiscovery(temp_storage)
        models = discovery.list_models()

        model = next(m for m in models if m.id == "test_model")
        assert model.name == "Test Model"

    def test_list_loras_empty(self, temp_storage):
        """No loras should return empty list."""
        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        assert loras == []

    def test_list_loras_with_config(self, temp_storage):
        """LoRA in subdirectory with config.json should be detected."""
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
        assert lora.enabled == True

    def test_list_loras_without_config(self, temp_storage):
        """LoRA in subdirectory without config should auto-generate name."""
        loras_dir = Path(temp_storage) / "loras"
        loras_dir.mkdir(parents=True)

        lora_dir = loras_dir / "test-lora"
        lora_dir.mkdir()

        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        lora = next(l for l in loras if l.id == "test-lora")
        assert lora.name == "Test Lora"
        assert lora.enabled == True

    def test_list_loras_safetensors_file(self, temp_storage):
        """Direct .safetensors LoRA file should be detected."""
        loras_dir = Path(temp_storage) / "loras"
        loras_dir.mkdir(parents=True)

        lora_file = loras_dir / "pixel_style.safetensors"
        lora_file.write_bytes(b"dummy lora data")

        discovery = ModelDiscovery(temp_storage)
        loras = discovery.list_loras()

        lora = next(l for l in loras if l.id == "pixel_style")
        assert lora.name == "Pixel Style"
        assert lora.enabled == True

    def test_get_model(self, temp_storage):
        """get_model should return model by ID."""
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
        """get_model should return None for nonexistent model."""
        discovery = ModelDiscovery(temp_storage)
        model = discovery.get_model("nonexistent")

        assert model is None

    def test_get_lora(self, temp_storage):
        """get_lora should return LoRA by ID."""
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

    def test_get_lora_not_found(self, temp_storage):
        """get_lora should return None for nonexistent LoRA."""
        discovery = ModelDiscovery(temp_storage)
        lora = discovery.get_lora("nonexistent")

        assert lora is None

    def test_ensure_dirs_creates_directories(self, temp_storage):
        """_ensure_dirs should create models and loras directories."""
        discovery = ModelDiscovery(temp_storage)
        discovery._ensure_dirs()

        assert (Path(temp_storage) / "models").exists()
        assert (Path(temp_storage) / "loras").exists()

    def test_multiple_models_and_loras(self, temp_storage):
        """Should detect multiple models and loras."""
        models_dir = Path(temp_storage) / "models"
        loras_dir = Path(temp_storage) / "loras"
        models_dir.mkdir(parents=True)
        loras_dir.mkdir(parents=True)

        (models_dir / "model1.safetensors").write_bytes(b"x")
        (models_dir / "model2.safetensors").write_bytes(b"x")
        (loras_dir / "lora1.safetensors").write_bytes(b"x")
        (loras_dir / "lora2.safetensors").write_bytes(b"x")

        discovery = ModelDiscovery(temp_storage)

        models = discovery.list_models()
        assert len(models) == 2
        model_ids = {m.id for m in models}
        assert model_ids == {"model1", "model2"}

        loras = discovery.list_loras()
        assert len(loras) == 2
        lora_ids = {l.id for l in loras}
        assert lora_ids == {"lora1", "lora2"}
