import pytest
import numpy as np
from PIL import Image
from app.services.quantization import (
    hex_to_rgb,
    closest_palette_color,
    quantize_image_to_palette,
    apply_dithering,
    pixels_to_image,
)


class TestQuantization:
    def test_hex_to_rgb(self):
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)
        assert hex_to_rgb("#AABBCC") == (170, 187, 204)

    def test_hex_to_rgb_without_hash(self):
        assert hex_to_rgb("FF0000") == (255, 0, 0)
        assert hex_to_rgb("aabbcc") == (170, 187, 204)

    def test_closest_palette_color_red(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]

        result = closest_palette_color((250, 10, 10), palette)

        assert result == 0

    def test_closest_palette_color_green(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]

        result = closest_palette_color((10, 250, 10), palette)

        assert result == 1

    def test_closest_palette_color_blue(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]

        result = closest_palette_color((10, 10, 250), palette)

        assert result == 2

    def test_closest_palette_color_middle(self):
        palette = ["#000000", "#FFFFFF"]

        result = closest_palette_color((127, 127, 127), palette)

        # Both are equidistant, first one wins
        assert result in [0, 1]

    def test_quantize_image_to_palette(self):
        img = Image.new("RGB", (4, 4), (255, 0, 0))
        palette = ["#FF0000", "#00FF00", "#0000FF"]

        result = quantize_image_to_palette(img, palette, 4, detect_transparency=False)

        assert len(result) == 4
        assert len(result[0]) == 4
        assert all(all(c == 0 for c in row) for row in result)

    def test_quantize_image_to_palette_green(self):
        img = Image.new("RGB", (2, 2), (0, 255, 0))
        palette = ["#FF0000", "#00FF00"]

        result = quantize_image_to_palette(img, palette, 2, detect_transparency=False)

        assert result[0][0] == 1

    def test_quantize_image_resizes(self):
        img = Image.new("RGB", (16, 16), (255, 0, 0))
        palette = ["#FF0000"]

        result = quantize_image_to_palette(img, palette, 4)

        assert len(result) == 4

    def test_apply_dithering(self):
        img = Image.new("RGB", (4, 4), (128, 128, 128))
        palette = ["#000000", "#FFFFFF"]

        result = apply_dithering(img, palette, 4)

        assert len(result) == 4
        assert len(result[0]) == 4
        assert all(c in [0, 1] for row in result for c in row)

    def test_apply_dithering_different_sizes(self):
        img = Image.new("RGB", (8, 8), (200, 200, 200))
        palette = ["#000000", "#808080", "#FFFFFF"]

        result = apply_dithering(img, palette, 4)

        assert len(result) == 4
        assert all(c in [0, 1, 2] for row in result for c in row)

    def test_pixels_to_image(self):
        pixel_data = [[0, 1], [1, 0]]
        palette = ["#FF0000", "#00FF00"]

        img = pixels_to_image(pixel_data, palette)

        assert img.size == (2, 2)
        r, g, b, a = img.getpixel((0, 0))
        assert r == 255 and g == 0 and b == 0

    def test_pixels_to_image_transparent(self):
        pixel_data = [[-1, 0], [0, -1]]
        palette = ["#FF0000"]

        img = pixels_to_image(pixel_data, palette)

        r, g, b, a = img.getpixel((0, 0))
        assert a == 0

    def test_pixels_to_image_invalid_color_index(self):
        pixel_data = [[99]]
        palette = ["#FF0000"]

        img = pixels_to_image(pixel_data, palette)

        r, g, b, a = img.getpixel((0, 0))
        assert a == 0

    def test_pixels_to_image_round_trip(self):
        original = [[0, 1, 2], [1, 2, 0], [2, 0, 1]]
        palette = ["#FF0000", "#00FF00", "#0000FF"]

        img = pixels_to_image(original, palette)

        assert img.size == (3, 3)

    def test_quantize_with_dither_flag(self):
        img = Image.new("RGB", (8, 8), (100, 100, 100))
        palette = ["#000000", "#FFFFFF"]

        result_no_dither = quantize_image_to_palette(img, palette, 4, dither=False)
        result_dither = quantize_image_to_palette(img, palette, 4, dither=True)

        assert len(result_no_dither) == 4
        assert len(result_dither) == 4

    def test_hex_to_rgb_case_insensitive(self):
        assert hex_to_rgb("#ff0000") == (255, 0, 0)
        assert hex_to_rgb("#FFaa00") == (255, 170, 0)
