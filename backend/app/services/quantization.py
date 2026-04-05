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


def optimize_palette_colors(
    image: Image.Image,
    target_palette: list[str],
    max_colors: Optional[int] = None,
) -> list[str]:
    """Optimize palette by selecting colors that best represent the image.

    Uses median-cut algorithm to find optimal color subset, then maps
    to provided palette colors.
    """
    img = image.convert("RGB")
    pixels = list(img.getdata())

    # Extract all unique colors with their counts
    color_counts: dict[tuple[int, int, int], int] = {}
    for r, g, b in pixels:
        color_counts[(r, g, b)] = color_counts.get((r, g, b), 0) + 1

    # Median cut to find representative colors
    num_colors = min(max_colors or 16, len(color_counts), target_palette)

    # Simple median cut implementation
    def median_cut(colors: list[tuple[int, int, int]], k: int) -> list[tuple[int, int, int]]:
        if k <= 0 or not colors:
            return []

        # Find the channel with greatest range
        channels = [(min(c[i] for c in colors), max(c[i] for c in colors)) for i in range(3)]
        ranges = [max_c - min_c for min_c, max_c in channels]
        split_channel = ranges.index(max(ranges))

        # Sort by that channel and split
        colors_sorted = sorted(colors, key=lambda c: c[split_channel])
        mid = len(colors_sorted) // 2

        left = median_cut(colors_sorted[:mid], k // 2)
        right = median_cut(colors_sorted[mid:], k - k // 2)

        if not left and not right:
            # Average all colors
            avg = (
                sum(c[0] for c in colors) // len(colors),
                sum(c[1] for c in colors) // len(colors),
                sum(c[2] for c in colors) // len(colors),
            )
            return [avg]

        return left + right

    # Get representative colors
    unique_colors = list(color_counts.keys())
    if len(unique_colors) <= num_colors:
        # Use unique colors, map to closest palette colors
        representative = unique_colors
    else:
        representative = median_cut(unique_colors, num_colors)
        if len(representative) < num_colors:
            representative = unique_colors[:num_colors]

    return representative


def remap_to_optimal_palette(
    pixel_data: list[list[int]],
    source_palette: list[str],
    target_palette: list[str],
) -> list[list[int]]:
    """Remap pixel data from source palette to target palette optimally.

    Uses the target palette colors directly - user provides their desired palette.
    """
    if not target_palette:
        return pixel_data

    target_rgb = [hex_to_rgb(c) for c in target_palette]
    new_pixel_data = []

    for row in pixel_data:
        new_row = []
        for color_idx in row:
            if color_idx < 0 or color_idx >= len(source_palette):
                # Default to transparent or first color
                new_row.append(-1 if len(target_palette) > 0 else 0)
            else:
                source_rgb = hex_to_rgb(source_palette[color_idx])
                # Find closest target color
                min_dist = float("inf")
                best_idx = 0
                for i, target in enumerate(target_rgb):
                    dist = sum((source_rgb[j] - target[j]) ** 2 for j in range(3))
                    if dist < min_dist:
                        min_dist = dist
                        best_idx = i
                new_row.append(best_idx)
        new_pixel_data.append(new_row)

    return new_pixel_data
