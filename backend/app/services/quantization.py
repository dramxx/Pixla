import numpy as np
from PIL import Image
from typing import Optional


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def closest_palette_color(pixel_rgb: tuple[int, int, int], palette: list[str]) -> int:
    min_dist = float("inf")
    closest_idx = 0

    palette_rgb = [hex_to_rgb(c) for c in palette]

    for idx, palette_rgb_val in enumerate(palette_rgb):
        # Convert to int to avoid overflow when dithering creates negative values
        p1 = tuple(int(v) for v in pixel_rgb)
        p2 = tuple(int(v) for v in palette_rgb_val)
        dist = sum((p1[i] - p2[i]) ** 2 for i in range(3))
        if dist < min_dist:
            min_dist = dist
            closest_idx = idx

    return closest_idx


def quantize_image_to_palette(
    image: Image.Image,
    palette: list[str],
    target_size: int,
    dither: bool = False,
) -> list[list[int]]:
    img = image.resize((target_size, target_size), Image.NEAREST if not dither else Image.LANCZOS)
    img = img.convert("RGB")
    img_array = np.array(img)

    pixel_data = []
    for y in range(target_size):
        row = []
        for x in range(target_size):
            pixel_rgb = tuple(img_array[y, x])
            closest = closest_palette_color(pixel_rgb, palette)
            row.append(closest)
        pixel_data.append(row)

    return pixel_data


def apply_dithering(
    image: Image.Image,
    palette: list[str],
    target_size: int,
) -> list[list[int]]:
    img = image.resize((target_size, target_size), Image.NEAREST).convert("RGB")
    img_array = np.array(img, dtype=np.float64)  # Use float64 to avoid overflow

    h, w = img_array.shape[:2]
    pixel_data = [[-1] * target_size for _ in range(target_size)]

    palette_rgb = np.array([hex_to_rgb(c) for c in palette])

    for y in range(h):
        for x in range(w):
            # Clip to valid range to prevent overflow
            old_pixel = np.clip(img_array[y, x], 0, 255)

            color_diff = old_pixel - palette_rgb
            dists = np.sum(color_diff**2, axis=1)
            new_idx = np.argmin(dists)
            new_color = palette_rgb[new_idx]

            pixel_data[y][x] = new_idx

            error = old_pixel - new_color

            if x + 1 < w:
                img_array[y, x + 1] = np.clip(img_array[y, x + 1] + error * 7 / 16, 0, 255)
            if y + 1 < h:
                if x > 0:
                    img_array[y + 1, x - 1] = np.clip(
                        img_array[y + 1, x - 1] + error * 3 / 16, 0, 255
                    )
                img_array[y + 1, x] = np.clip(img_array[y + 1, x] + error * 5 / 16, 0, 255)
                if x + 1 < w:
                    img_array[y + 1, x + 1] = np.clip(
                        img_array[y + 1, x + 1] + error * 1 / 16, 0, 255
                    )

    return pixel_data


def pixels_to_image(
    pixel_data: list[list[int]],
    palette: list[str],
) -> Image.Image:
    size = len(pixel_data)
    img = Image.new("RGBA", (size, size))

    for y, row in enumerate(pixel_data):
        for x, color_idx in enumerate(row):
            if color_idx >= 0 and color_idx < len(palette):
                hex_color = palette[color_idx]
                r, g, b = hex_to_rgb(hex_color)
                img.putpixel((x, y), (r, g, b, 255))
            else:
                img.putpixel((x, y), (0, 0, 0, 0))

    return img
