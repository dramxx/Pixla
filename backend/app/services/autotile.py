"""Autotile/tileset generation - creates 16 variants of a block tile."""

from PIL import Image
from typing import List


def _darken_color(hex_color: str, amount: float) -> str:
    """Darken a hex color by a percentage."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))

    return f"#{r:02x}{g:02x}{b:02x}"


def generate_autotile_variant(base_img: Image.Image, mask: int, size: int) -> Image.Image:
    """
    Apply edge shading, outlines, and rounded corners for a bitmask variant.

    Bitmask: TOP=1, RIGHT=2, BOTTOM=4, LEFT=8
    - 0 = isolated (all edges exposed)
    - 15 = fully surrounded (base tile)
    """
    img = base_img.copy()
    pixels = img.load()

    top_exposed = (mask & 1) == 0
    right_exposed = (mask & 2) == 0
    bottom_exposed = (mask & 4) == 0
    left_exposed = (mask & 8) == 0

    band = max(2, size // 5)
    intensity = 0.15

    for y in range(size):
        for x in range(size):
            r, g, b, a = pixels[x, y]
            if a < 25:
                continue

            f = 0.0
            if top_exposed and y < band:
                f += intensity * (1 - y / band)
            if left_exposed and x < band:
                f += intensity * 0.6 * (1 - x / band)
            if bottom_exposed:
                d = size - 1 - y
                if d < band:
                    f -= intensity * (1 - d / band)
            if right_exposed:
                d = size - 1 - x
                if d < band:
                    f -= intensity * 0.6 * (1 - d / band)

            if f != 0:
                r = max(0, min(255, int(r + f * 255)))
                g = max(0, min(255, int(g + f * 255)))
                b = max(0, min(255, int(b + f * 255)))
                pixels[x, y] = (r, g, b, a)

    outline_w = max(1, size // 16)
    for y in range(size):
        for x in range(size):
            r, g, b, a = pixels[x, y]
            if a < 25:
                continue

            hit = False
            if top_exposed and y < outline_w:
                hit = True
            if bottom_exposed and y >= size - outline_w:
                hit = True
            if left_exposed and x < outline_w:
                hit = True
            if right_exposed and x >= size - outline_w:
                hit = True

            if hit:
                dr = max(0, int(r * 0.6))
                dg = max(0, int(g * 0.6))
                db = max(0, int(b * 0.6))
                pixels[x, y] = (dr, dg, db, a)

    radius = max(1, size // 10)
    for y in range(size):
        for x in range(size):
            clear = False
            if top_exposed and left_exposed and x + y < radius:
                clear = True
            if top_exposed and right_exposed and (size - 1 - x) + y < radius:
                clear = True
            if bottom_exposed and left_exposed and x + (size - 1 - y) < radius:
                clear = True
            if bottom_exposed and right_exposed and (size - 1 - x) + (size - 1 - y) < radius:
                clear = True

            if clear:
                pixels[x, y] = (0, 0, 0, 0)

    return img


def generate_tileset(
    pixel_data: List[List[int]], palette: List[str], size: int
) -> dict[int, Image.Image]:
    """Generate all 16 autotile variants from base pixel data."""
    from app.services.quantization import pixels_to_image

    base_img = pixels_to_image(pixel_data, palette)
    variants = {}

    for mask in range(16):
        variants[mask] = generate_autotile_variant(base_img, mask, size)

    return variants
