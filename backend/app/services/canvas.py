import io
import base64
import math
from typing import Optional
from PIL import Image


class Canvas:
    def __init__(self, size: int, palette: list[str], pixels: Optional[list[list[int]]] = None):
        self.size = size
        self.palette = palette
        self.pixels = pixels if pixels else [[-1] * size for _ in range(size)]

    def set_pixel(self, x: int, y: int, color: int) -> str:
        if not (0 <= x < self.size and 0 <= y < self.size):
            return f"Error: ({x},{y}) out of bounds (0-{self.size - 1})"
        if color < -1 or color >= len(self.palette):
            return f"Error: color index {color} invalid (use -1 to {len(self.palette) - 1})"

        self.pixels[y][x] = color
        return f"Set ({x},{y}) to {color}"

    def get_pixel(self, x: int, y: int) -> int:
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.pixels[y][x]
        return -1

    def fill_rect(self, x1: int, y1: int, x2: int, y2: int, color: int) -> str:
        if color < -1 or color >= len(self.palette):
            return f"Error: color index {color} invalid"

        count = 0
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        for y in range(max(0, y1), min(self.size, y2 + 1)):
            for x in range(max(0, x1), min(self.size, x2 + 1)):
                self.pixels[y][x] = color
                count += 1
        return f"Filled rect ({x1},{y1})-({x2},{y2}) with {color}, {count} pixels"

    def fill_row(self, y: int, x_start: int, x_end: int, color: int) -> str:
        if color < -1 or color >= len(self.palette):
            return f"Error: color index {color} invalid"
        count = 0
        for x in range(max(0, x_start), min(self.size, x_end + 1)):
            if 0 <= y < self.size:
                self.pixels[y][x] = color
                count += 1
        return f"Filled row y={y}, {count} pixels"

    def fill_column(self, x: int, y_start: int, y_end: int, color: int) -> str:
        if color < -1 or color >= len(self.palette):
            return f"Error: color index {color} invalid"
        count = 0
        for y in range(max(0, y_start), min(self.size, y_end + 1)):
            if 0 <= x < self.size:
                self.pixels[y][x] = color
                count += 1
        return f"Filled column x={x}, {count} pixels"

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: int) -> str:
        if color < -1 or color >= len(self.palette):
            return f"Error: color index {color} invalid"

        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        count = 0
        cx, cy = x1, y1

        while True:
            if 0 <= cx < self.size and 0 <= cy < self.size:
                self.pixels[cy][cx] = color
                count += 1
            if cx == x2 and cy == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
        return f"Drew line, {count} pixels"

    def draw_circle(self, cx: int, cy: int, radius: int, color: int, fill: bool = True) -> int:
        count = 0
        for y in range(max(0, cy - radius), min(self.size, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.size, cx + radius + 1)):
                dx, dy = x - cx, y - cy
                dist_sq = dx * dx + dy * dy
                r_sq = radius * radius

                if fill:
                    if dist_sq <= r_sq:
                        self.pixels[y][x] = color
                        count += 1
                else:
                    if abs(dist_sq - r_sq) <= radius * 2:
                        self.pixels[y][x] = color
                        count += 1
        return count

    def draw_ellipse(
        self, cx: int, cy: int, rx: int, ry: int, color: int, fill: bool = True
    ) -> int:
        count = 0
        for y in range(max(0, cy - ry), min(self.size, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(self.size, cx + rx + 1)):
                dx, dy = (x - cx) / max(rx, 1), (y - cy) / max(ry, 1)
                dist = dx * dx + dy * dy
                if fill:
                    if dist <= 1.0:
                        self.pixels[y][x] = color
                        count += 1
                else:
                    if abs(dist - 1.0) <= 0.3:
                        self.pixels[y][x] = color
                        count += 1
        return count

    def draw_triangle(
        self, x1: int, y1: int, x2: int, y2: int, x3: int, y3: int, color: int
    ) -> int:
        def sign(px, py, ax, ay, bx, by):
            return (px - bx) * (ay - by) - (ax - bx) * (py - by)

        min_x = max(0, min(x1, x2, x3))
        max_x = min(self.size - 1, max(x1, x2, x3))
        min_y = max(0, min(y1, y2, y3))
        max_y = min(self.size - 1, max(y1, y2, y3))

        count = 0
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                d1 = sign(x, y, x1, y1, x2, y2)
                d2 = sign(x, y, x2, y2, x3, y3)
                d3 = sign(x, y, x3, y3, x1, y1)
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                if not (has_neg and has_pos):
                    self.pixels[y][x] = color
                    count += 1
        return count

    def draw_rotated_rect(
        self, cx: int, cy: int, w: int, h: int, angle_deg: float, color: int
    ) -> int:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        hw, hh = w / 2, h / 2
        max_r = math.ceil(math.sqrt(hw * hw + hh * hh)) + 1
        count = 0
        for py in range(max(0, cy - max_r), min(self.size, cy + max_r + 1)):
            for px in range(max(0, cx - max_r), min(self.size, cx + max_r + 1)):
                dx = px - cx
                dy = py - cy
                lx = dx * cos_a + dy * sin_a
                ly = -dx * sin_a + dy * cos_a
                if abs(lx) <= hw and abs(ly) <= hh:
                    self.pixels[py][px] = color
                    count += 1
        return count

    @staticmethod
    def _hash_noise(x: int, y: int, seed: int) -> float:
        n = x * 374761393 + y * 668265263 + seed * 1274126177
        n = ((n ^ (n >> 13)) * 1274126177) & 0x7FFFFFFF
        n = n ^ (n >> 16)
        return (n & 0x7FFFFFFF) / 0x7FFFFFFF

    def fill_noise(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        colors: list[int],
        seed: int = 42,
        scale: float = 1.0,
    ) -> int:
        count = 0
        n_colors = len(colors)
        if n_colors == 0:
            return 0
        for y in range(max(0, y1), min(self.size, y2 + 1)):
            for x in range(max(0, x1), min(self.size, x2 + 1)):
                n = self._hash_noise(int(x * scale), int(y * scale), seed)
                idx = int(n * n_colors) % n_colors
                self.pixels[y][x] = colors[idx]
                count += 1
        return count

    def fill_voronoi(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        colors: list[int],
        num_points: int = 8,
        seed: int = 42,
    ) -> int:
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        points = []
        for i in range(num_points):
            px = x1 + int(self._hash_noise(i, 0, seed) * w)
            py = y1 + int(self._hash_noise(0, i, seed + 99) * h)
            points.append((px, py, colors[i % len(colors)]))

        count = 0
        for y in range(max(0, y1), min(self.size, y2 + 1)):
            for x in range(max(0, x1), min(self.size, x2 + 1)):
                best_dist = float("inf")
                best_color = colors[0]
                for px, py, pc in points:
                    d = (x - px) ** 2 + (y - py) ** 2
                    if d < best_dist:
                        best_dist = d
                        best_color = pc
                self.pixels[y][x] = best_color
                count += 1
        return count

    def fill_noise_circle(
        self, cx: int, cy: int, radius: int, colors: list[int], seed: int = 42
    ) -> int:
        count = 0
        n_colors = len(colors)
        if n_colors == 0:
            return 0
        for y in range(max(0, cy - radius), min(self.size, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.size, cx + radius + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    n = self._hash_noise(x, y, seed)
                    self.pixels[y][x] = colors[int(n * n_colors) % n_colors]
                    count += 1
        return count

    def to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        for y, row in enumerate(self.pixels):
            for x, idx in enumerate(row):
                if 0 <= idx < len(self.palette):
                    h = self.palette[idx]
                    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
                    img.putpixel((x, y), (r, g, b, 255))
        return img

    def to_image_b64(self, scale: int = 64) -> str:
        img = self.to_image().resize((scale, scale), Image.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def to_grid_string(self) -> str:
        """Convert canvas to compact string representation."""
        # For small canvases, show full grid. For large, condensed.
        if self.size <= 16:
            header = "    " + " ".join(f"{x:>3}" for x in range(self.size))
            rows = [
                f"{y:>3} " + " ".join(f"{v:>3}" for v in row) for y, row in enumerate(self.pixels)
            ]
            return header + "\n" + "\n".join(rows)

        # For larger canvases (32+), show condensed version
        # Group 2x2 pixels into cells
        cell_size = 2
        condensed_size = self.size // cell_size
        condensed = []
        for y in range(0, self.size, cell_size):
            row_str = ""
            for x in range(0, self.size, cell_size):
                # Get representative color (center of cell)
                color = self.pixels[y + cell_size // 2][x + cell_size // 2]
                if color == -1:
                    row_str += " . "
                else:
                    row_str += f" {color} "
            condensed.append(row_str)

        # Also show sparse coordinate list of non-empty pixels
        pixels = [
            (x, y, self.pixels[y][x])
            for y in range(self.size)
            for x in range(self.size)
            if self.pixels[y][x] >= 0
        ]

        grid = f"[{self.size}x{self.size} condensed {cell_size}x{cell_size} blocks]\n" + "\n".join(
            condensed
        )

        if pixels:
            # Show first 30 non-empty pixels
            sample = pixels[:30]
            grid += f"\n\nNon-empty pixels ({len(pixels)} total): {sample}"
            if len(pixels) > 30:
                grid += f" ... +{len(pixels) - 30} more"

        return grid

    def get_color_usage(self) -> dict[str, int]:
        usage = {}
        for row in self.pixels:
            for val in row:
                if val == -1:
                    key = "transparent"
                elif 0 <= val < len(self.palette):
                    key = f"{val}({self.palette[val]})"
                else:
                    key = f"invalid({val})"
                usage[key] = usage.get(key, 0) + 1
        return usage

    def view_canvas(self) -> str:
        """View canvas state - simplified for LLM to avoid context overflow."""
        grid = self.to_grid_string()

        # Count colors - simplified without image
        color_counts: dict[int, int] = {}
        for row in self.pixels:
            for v in row:
                color_counts[v] = color_counts.get(v, 0) + 1

        summary = []
        for idx, count in sorted(color_counts.items(), key=lambda x: -x[1]):
            if idx == -1:
                summary.append(f"transparent: {count}px")
            elif 0 <= idx < len(self.palette):
                summary.append(f"{idx}({self.palette[idx]}): {count}px")

        total = sum(c for i, c in color_counts.items() if i >= 0)
        # NO base64 image - too large for LLM context
        return f"{grid}\n\nCOLOR USAGE: {', '.join(summary[:8])}\nFilled: {total}/{self.size * self.size}px"

    def finish(self) -> str:
        # Check if canvas is empty (all -1 pixels)
        filled_pixels = sum(1 for row in self.pixels for p in row if p >= 0)
        if filled_pixels == 0:
            return "ERROR: Cannot finish - canvas is empty. Draw something first using the canvas tools."
        return "FINISHED"
