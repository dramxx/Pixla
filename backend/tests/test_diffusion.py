import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile


class TestDiffusionLoRA:
    """Tests for LoRA loading and scaling logic - isolated from actual model loading."""

    def test_load_loras_returns_early_when_none(self):
        """Should return early when loras is None."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = mock_pipeline

        service.load_loras(None)

        mock_pipeline.disable_lora.assert_not_called()
        mock_pipeline.load_lora_weights.assert_not_called()

    def test_load_loras_returns_early_when_empty_list(self):
        """Should return early when loras is empty list."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = mock_pipeline

        service.load_loras([])

        # Returns early, no LoRA methods called
        mock_pipeline.disable_lora.assert_not_called()
        mock_pipeline.load_lora_weights.assert_not_called()

    def test_load_loras_returns_early_when_pipeline_none(self):
        """Should return early when pipeline is None."""
        from app.services.diffusion import DiffusionService

        service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = None

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "lora.safetensors"
            lora_file.write_bytes(b"x")

            service.load_loras([{"path": str(lora_file), "scale": 1.0}])

            # No methods called because pipeline is None

    def test_load_loras_disables_first(self):
        """Should call disable_lora before loading new LoRAs."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "test.safetensors"
            lora_file.write_bytes(b"x")

            service = DiffusionService(model_id=tmpdir, device="cpu", dtype="float32")
            service._pipeline = mock_pipeline

            service.load_loras([{"path": str(lora_file), "scale": 1.0}])

            mock_pipeline.disable_lora.assert_called_once()

    def test_load_loras_calls_correct_methods(self):
        """LoRA loading should call load_lora_weights and set_adapters with scale."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "test_lora.safetensors"
            lora_file.write_bytes(b"dummy lora data")

            service = DiffusionService(model_id=tmpdir, device="cpu", dtype="float32")
            service._pipeline = mock_pipeline

            loras = [{"path": str(lora_file), "scale": 0.8}]
            service.load_loras(loras)

            mock_pipeline.load_lora_weights.assert_called_once()
            call_args = mock_pipeline.load_lora_weights.call_args
            assert "test_lora" in call_args[1].get("adapter_name", "")

            mock_pipeline.set_adapters.assert_called_once()
            args, kwargs = mock_pipeline.set_adapters.call_args
            adapter_names = args[0] if args else kwargs.get("adapter_names", [])
            adapter_weights = args[1] if len(args) > 1 else kwargs.get("adapter_weights", [])
            assert adapter_names == ["test_lora"]
            assert adapter_weights == [0.8]

    def test_load_loras_with_multiple_scales(self):
        """Should apply different scales to multiple LoRAs."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        with tempfile.TemporaryDirectory() as tmpdir:
            lora1 = Path(tmpdir) / "lora1.safetensors"
            lora2 = Path(tmpdir) / "lora2.safetensors"
            lora1.write_bytes(b"x")
            lora2.write_bytes(b"x")

            service = DiffusionService(model_id=tmpdir, device="cpu", dtype="float32")
            service._pipeline = mock_pipeline

            loras = [
                {"path": str(lora1), "scale": 0.5},
                {"path": str(lora2), "scale": 1.5},
            ]
            service.load_loras(loras)

            mock_pipeline.set_adapters.assert_called_once()
            args, kwargs = mock_pipeline.set_adapters.call_args
            adapter_weights = args[1] if len(args) > 1 else kwargs.get("adapter_weights", [])
            assert adapter_weights == [0.5, 1.5]

    def test_load_loras_handles_missing_file(self):
        """Should warn but not fail when LoRA file not found."""
        mock_pipeline = MagicMock()

        from app.services import diffusion as diffusion_module
        from app.utils.logging import diffusion_logger

        service = diffusion_module.DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = mock_pipeline

        with patch.object(diffusion_logger, "warning") as mock_warning:
            service.load_loras([{"path": "/nonexistent/lora.safetensors", "scale": 1.0}])

            assert any("LoRA not found" in str(c) for c in mock_warning.call_args_list)
            mock_pipeline.load_lora_weights.assert_not_called()

    def test_load_loras_default_scale(self):
        """Should use scale 1.0 when not specified."""
        mock_pipeline = MagicMock()

        from app.services.diffusion import DiffusionService

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "lora.safetensors"
            lora_file.write_bytes(b"x")

            service = DiffusionService(model_id=tmpdir, device="cpu", dtype="float32")
            service._pipeline = mock_pipeline

            # No scale specified
            service.load_loras([{"path": str(lora_file)}])

            args, kwargs = mock_pipeline.set_adapters.call_args
            adapter_weights = args[1] if len(args) > 1 else kwargs.get("adapter_weights", [])
            assert adapter_weights == [1.0]

    def test_load_loras_prints_loaded(self):
        """Should print when LoRA is loaded."""
        mock_pipeline = MagicMock()

        from app.services import diffusion as diffusion_module

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "test.safetensors"
            lora_file.write_bytes(b"x")

            service = diffusion_module.DiffusionService(
                model_id=tmpdir, device="cpu", dtype="float32"
            )
            service._pipeline = mock_pipeline

            from app.utils.logging import diffusion_logger

            with patch.object(diffusion_logger, "info") as mock_info:
                service.load_loras([{"path": str(lora_file), "scale": 0.5}])

                logged_output = [str(c) for c in mock_info.call_args_list]
                assert any("Loaded LoRA" in o for o in logged_output)
                assert any("scale=0.5" in o for o in logged_output)


class TestDiffusionUnload:
    """Tests for pipeline cleanup."""

    def test_unload_clears_pipeline(self):
        """unload should clear pipeline."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()
        service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = mock_pipeline

        service.unload()

        assert service._pipeline is None

    def test_unload_clears_cuda_when_cuda(self):
        """unload should clear CUDA cache when using cuda."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()
        service = DiffusionService(model_id="dummy", device="cuda", dtype="float32")
        service._pipeline = mock_pipeline

        with patch("torch.cuda.empty_cache") as mock_cache:
            service.unload()

            mock_cache.assert_called_once()

    def test_unload_nothing_when_already_unloaded(self):
        """unload should handle already unloaded pipeline."""
        from app.services.diffusion import DiffusionService

        service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
        service._pipeline = None

        # Should not raise
        service.unload()

        assert service._pipeline is None


class TestGeneratePixelArtReference:
    """Tests for generation with LoRA integration."""

    def test_generate_requires_pipeline(self):
        """generate_pixel_art_reference should call _load_model."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()

        # Mock _load_model to avoid actual model loading
        with patch.object(DiffusionService, "_load_model") as mock_load:
            service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")

            # Set pipeline to skip load
            service._pipeline = mock_pipeline

            service.generate_pixel_art_reference(
                prompt="test",
                sprite_type="block",
                size=512,
                loras=None,
            )

            mock_load.assert_called()

    def test_generate_with_loras_calls_load(self):
        """generate_pixel_art_reference should call load_loras when loras provided."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            lora_file = Path(tmpdir) / "lora.safetensors"
            lora_file.write_bytes(b"x")

            with patch.object(DiffusionService, "_load_model"):
                with patch.object(DiffusionService, "load_loras") as mock_load_loras:
                    service = DiffusionService(model_id=tmpdir, device="cpu", dtype="float32")
                    service._pipeline = mock_pipeline

                    loras = [{"path": str(lora_file), "scale": 0.7}]
                    service.generate_pixel_art_reference(
                        prompt="test prompt",
                        sprite_type="block",
                        size=512,
                        loras=loras,
                    )

                    mock_load_loras.assert_called_once_with(loras)

    def test_generate_without_loras_skips_load(self):
        """generate_pixel_art_reference should not call load_loras when None."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()

        with patch.object(DiffusionService, "_load_model"):
            with patch.object(DiffusionService, "load_loras") as mock_load_loras:
                service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
                service._pipeline = mock_pipeline

                service.generate_pixel_art_reference(
                    prompt="test",
                    sprite_type="block",
                    size=512,
                    loras=None,
                )

                mock_load_loras.assert_not_called()

    def test_generate_with_custom_steps_and_guidance(self):
        """generate_pixel_art_reference should use custom steps and guidance when provided."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()

        # Mock the generate method directly
        with patch.object(DiffusionService, "_load_model"):
            with patch.object(DiffusionService, "load_loras"):
                with patch.object(DiffusionService, "generate") as mock_generate:
                    mock_generate.return_value = MagicMock()

                    service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
                    service._pipeline = mock_pipeline

                    service.generate_pixel_art_reference(
                        prompt="test",
                        sprite_type="block",
                        size=512,
                        num_inference_steps=30,
                        guidance_scale=9.5,
                    )

                    # Verify the generate method was called with custom params
                    call_kwargs = mock_generate.call_args[1]
                    assert call_kwargs["num_inference_steps"] == 30
                    assert call_kwargs["guidance_scale"] == 9.5

    def test_generate_uses_defaults_when_not_specified(self):
        """generate_pixel_art_reference should use defaults when params are None."""
        from app.services.diffusion import DiffusionService

        mock_pipeline = MagicMock()

        with patch.object(DiffusionService, "_load_model"):
            with patch.object(DiffusionService, "load_loras"):
                with patch.object(DiffusionService, "generate") as mock_generate:
                    mock_generate.return_value = MagicMock()

                    service = DiffusionService(model_id="dummy", device="cpu", dtype="float32")
                    service._pipeline = mock_pipeline

                    service.generate_pixel_art_reference(
                        prompt="test",
                        sprite_type="block",
                        size=512,
                        num_inference_steps=None,
                        guidance_scale=None,
                    )

                    call_kwargs = mock_generate.call_args[1]
                    assert call_kwargs["num_inference_steps"] == 25
                    assert call_kwargs["guidance_scale"] == 8.0
