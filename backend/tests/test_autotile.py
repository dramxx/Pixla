import pytest
from PIL import Image
from app.services.autotile import (
    _darken_color,
    generate_autotile_variant,
    generate_tileset,
)
from app.services.quantization import pixels_to_image


class TestAutotile:
    def test_darken_color_full(self):
        result = _darken_color("#FF0000", 1.0)

        assert result == "#000000"

    def test_darken_color_partial(self):
        result = _darken_color("#FF0000", 0.5)

        assert result == "#7f0000"

    def test_darken_color_no_change(self):
        result = _darken_color("#808080", 0.0)

        assert result == "#808080"

    def test_darken_color_minimum_zero(self):
        result = _darken_color("#000000", 1.0)

        assert result == "#000000"

    def test_generate_autotile_variant_isolated(self):
        pixel_data = [[0] * 16 for _ in range(16)]
        palette = ["#FF0000"]
        img = pixels_to_image(pixel_data, palette)

        result = generate_autotile_variant(img, 0, 16)

        assert isinstance(result, Image.Image)
        assert result.size == (16, 16)

    def test_generate_autotile_variant_fully_surrounded(self):
        pixel_data = [[0] * 16 for _ in range(16)]
        palette = ["#FF0000"]
        img = pixels_to_image(pixel_data, palette)

        result = generate_autotile_variant(img, 15, 16)

        assert isinstance(result, Image.Image)
        assert result.size == (16, 16)

    def test_generate_autotile_variant_top_only(self):
        pixel_data = [[0] * 16 for _ in range(16)]
        palette = ["#FF0000"]
        img = pixels_to_image(pixel_data, palette)

        result = generate_autotile_variant(img, 14, 16)

        assert isinstance(result, Image.Image)

    def test_generate_autotile_variant_different_sizes(self):
        pixel_data = [[0] * 8 for _ in range(8)]
        palette = ["#FF0000"]
        img = pixels_to_image(pixel_data, palette)

        result = generate_autotile_variant(img, 5, 8)

        assert result.size == (8, 8)

    def test_generate_tileset_returns_16_variants(self):
        pixel_data = [[0] * 16 for _ in range(16)]
        palette = ["#FF0000"]

        variants = generate_tileset(pixel_data, palette, 16)

        assert len(variants) == 16
        for mask in range(16):
            assert mask in variants
            assert isinstance(variants[mask], Image.Image)

    def test_generate_tileset_all_masks(self):
        pixel_data = [[1] * 16 + [0] * 0 for _ in range(16)]
        palette = ["#000000", "#FFFFFF"]

        # Note: pixel_data determines size, size param is for variant rendering
        variants = generate_tileset(pixel_data, palette, 16)

        for mask in range(16):
            assert mask in variants
            assert variants[mask].size == (16, 16)

    def test_generate_autotile_preserves_transparency(self):
        pixel_data = [[-1] * 16 for _ in range(16)]
        palette = ["#FF0000"]
        img = pixels_to_image(pixel_data, palette)

        result = generate_autotile_variant(img, 0, 16)

        pixels = result.load()
        assert pixels[0, 0][3] == 0
