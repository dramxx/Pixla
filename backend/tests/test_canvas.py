import pytest
from app.services.canvas import Canvas


class TestCanvas:
    def test_init_creates_empty_canvas(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]
        canvas = Canvas(8, palette)

        assert canvas.size == 8
        assert canvas.palette == palette
        assert canvas.pixels == [[-1] * 8 for _ in range(8)]

    def test_init_with_existing_pixels(self):
        palette = ["#FF0000", "#00FF00"]
        pixels = [[0, 1], [1, 0]]
        canvas = Canvas(2, palette, pixels)

        assert canvas.pixels == pixels

    def test_set_pixel_valid(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(4, palette)

        result = canvas.set_pixel(2, 2, 1)

        assert canvas.pixels[2][2] == 1
        assert "Set (2,2) to 1" in result

    def test_set_pixel_out_of_bounds(self):
        palette = ["#FF0000"]
        canvas = Canvas(4, palette)

        result = canvas.set_pixel(5, 5, 0)

        assert "out of bounds" in result

    def test_set_pixel_invalid_color(self):
        palette = ["#FF0000"]
        canvas = Canvas(4, palette)

        result = canvas.set_pixel(0, 0, 5)

        assert "invalid" in result

    def test_get_pixel_valid(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(4, palette)
        canvas.pixels[2][3] = 1

        assert canvas.get_pixel(3, 2) == 1

    def test_get_pixel_out_of_bounds(self):
        palette = ["#FF0000"]
        canvas = Canvas(4, palette)

        assert canvas.get_pixel(10, 10) == -1

    def test_fill_rect(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(8, palette)

        result = canvas.fill_rect(2, 2, 5, 5, 1)

        for y in range(2, 6):
            for x in range(2, 6):
                assert canvas.pixels[y][x] == 1

    def test_fill_rect_invalid_color(self):
        palette = ["#FF0000"]
        canvas = Canvas(8, palette)

        result = canvas.fill_rect(0, 0, 3, 3, 5)

        assert "invalid" in result

    def test_fill_row(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(8, palette)

        result = canvas.fill_row(3, 1, 6, 1)

        for x in range(1, 7):
            assert canvas.pixels[3][x] == 1

    def test_fill_column(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(8, palette)

        result = canvas.fill_column(4, 1, 6, 1)

        for y in range(1, 7):
            assert canvas.pixels[y][4] == 1

    def test_draw_line_horizontal(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(10, palette)

        canvas.draw_line(2, 5, 7, 5, 1)

        for x in range(2, 8):
            assert canvas.pixels[5][x] == 1

    def test_draw_line_vertical(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(10, palette)

        canvas.draw_line(3, 2, 3, 7, 1)

        for y in range(2, 8):
            assert canvas.pixels[y][3] == 1

    def test_draw_line_diagonal(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(10, palette)

        canvas.draw_line(2, 2, 7, 7, 1)

        assert canvas.pixels[2][2] == 1
        assert canvas.pixels[7][7] == 1

    def test_draw_circle_fill(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.draw_circle(8, 8, 3, 1, fill=True)

        assert count > 0
        assert canvas.pixels[8][8] == 1

    def test_draw_circle_outline(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.draw_circle(8, 8, 3, 1, fill=False)

        assert count > 0

    def test_draw_ellipse(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.draw_ellipse(8, 8, 4, 2, 1, fill=True)

        assert count > 0

    def test_draw_triangle(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.draw_triangle(8, 2, 4, 12, 12, 12, 1)

        assert count > 0
        assert canvas.pixels[2][8] == 1
        assert canvas.pixels[12][4] == 1
        assert canvas.pixels[12][12] == 1

    def test_draw_rotated_rect(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.draw_rotated_rect(8, 8, 6, 4, 45, 1)

        assert count > 0

    def test_fill_noise(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]
        canvas = Canvas(8, palette)

        count = canvas.fill_noise(0, 0, 7, 7, [0, 1, 2], seed=42)

        assert count == 64
        for y in range(8):
            for x in range(8):
                assert canvas.pixels[y][x] in [0, 1, 2]

    def test_fill_noise_with_empty_colors(self):
        palette = ["#FF0000"]
        canvas = Canvas(8, palette)

        count = canvas.fill_noise(0, 0, 7, 7, [])

        assert count == 0

    def test_fill_noise_circle(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(16, palette)

        count = canvas.fill_noise_circle(8, 8, 5, [0, 1], seed=42)

        assert count > 0

    def test_fill_voronoi(self):
        palette = ["#FF0000", "#00FF00", "#0000FF"]
        canvas = Canvas(8, palette)

        count = canvas.fill_voronoi(0, 0, 7, 7, [0, 1, 2], num_points=4, seed=42)

        assert count == 64

    def test_to_image(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(2, palette)
        canvas.pixels = [[0, 1], [1, 0]]

        img = canvas.to_image()

        assert img.size == (2, 2)
        r, g, b, a = img.getpixel((0, 0))
        assert r == 255 and g == 0 and b == 0

    def test_to_image_b64(self):
        palette = ["#FF0000"]
        canvas = Canvas(2, palette)
        canvas.pixels = [[0, 0], [0, 0]]

        b64 = canvas.to_image_b64()

        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_to_grid_string(self):
        palette = ["#FF0000"]
        canvas = Canvas(3, palette)
        canvas.pixels = [[0, 1, -1], [-1, 0, 1], [1, -1, 0]]

        grid = canvas.to_grid_string()

        assert "  0   1   2" in grid
        assert "  0" in grid
        assert "  1" in grid
        assert "  2" in grid

    def test_get_color_usage(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(2, palette)
        canvas.pixels = [[0, 1], [1, 0]]

        usage = canvas.get_color_usage()

        assert usage["0(#FF0000)"] == 2
        assert usage["1(#00FF00)"] == 2

    def test_view_canvas(self):
        palette = ["#FF0000"]
        canvas = Canvas(2, palette)
        canvas.pixels = [[0, 0], [0, 0]]

        view = canvas.view_canvas()

        assert "COLOR USAGE" in view
        assert "Filled:" in view

    def test_finish(self):
        palette = ["#FF0000"]
        canvas = Canvas(4, palette)
        # Add some pixels first - finish should work with non-empty canvas
        canvas.pixels[0][0] = 0
        canvas.pixels[1][1] = 0

        result = canvas.finish()

        assert result == "FINISHED"

    def test_finish_empty_returns_error(self):
        """Test that finish() on empty canvas returns error."""
        palette = ["#FF0000"]
        canvas = Canvas(4, palette)
        # Don't add any pixels - canvas is empty

        result = canvas.finish()

        assert (
            result
            == "ERROR: Cannot finish - canvas is empty. Draw something first using the canvas tools."
        )

    def test_fill_rect_clips_to_bounds(self):
        palette = ["#FF0000", "#00FF00"]
        canvas = Canvas(8, palette)

        canvas.fill_rect(-2, -2, 12, 12, 1)

        assert canvas.pixels[0][0] == 1
        assert canvas.pixels[7][7] == 1
        assert canvas.pixels[-1][-1] == 1
