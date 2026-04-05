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
    detect_transparency: bool = True,
) -> list[list[int]]:
    # Resize to target size first
    img = image.resize((target_size, target_size), Image.NEAREST if not dither else Image.LANCZOS)
    img = img.convert("RGBA")  # Need RGBA to detect transparency
    img_array = np.array(img)

    h, w = img_array.shape[:2]
    has_alpha = img_array.shape[2] == 4

    # First pass: quantize to palette
    pixel_data = []
    for y in range(target_size):
        row = []
        for x in range(target_size):
            pixel = img_array[y, x]

            if has_alpha and pixel[3] < 128:
                row.append(-1)  # Transparent pixel (alpha=0)
            else:
                pixel_rgb = tuple(pixel[:3])
                closest = closest_palette_color(pixel_rgb, palette)
                row.append(closest)
        pixel_data.append(row)

    # Second pass: detect background via flood-fill from corners
    # Only mark as transparent if corner pixels are uniform and connected
    if detect_transparency:
        pixel_data = detect_background(pixel_data)

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


def detect_background(pixel_data: list[list[int]]) -> list[list[int]]:
    """Detect and mark background as transparent via flood-fill from corners."""
    h = len(pixel_data)
    w = len(pixel_data[0]) if h > 0 else 0
    if w == 0 or h == 0:
        return pixel_data

    # Get corner colors
    corner_colors = set()
    for corner in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]:
        corner_colors.add(pixel_data[corner[0]][corner[1]])

    # If all corners same color, flood-fill from corners to find background
    if len(corner_colors) == 1:
        bg_color = list(corner_colors)[0]
        if bg_color >= 0:  # Valid palette index
            # Flood-fill from all corners
            visited = set()
            stack = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]

            while stack:
                y, x = stack.pop()
                if (y, x) in visited:
                    continue
                if y < 0 or y >= h or x < 0 or x >= w:
                    continue
                if pixel_data[y][x] != bg_color:
                    continue

                visited.add((y, x))
                stack.extend([(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)])

            # Mark all visited (background) as -1
            for y, x in visited:
                pixel_data[y][x] = -1

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
