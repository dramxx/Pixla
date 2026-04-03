import pytest
from app.services.agent import (
    build_system_prompt,
    build_continuation_prompt,
    parse_tool_calls,
    execute_tool,
    Session,
)
from app.services.canvas import Canvas


class TestAgentPrompts:
    def test_build_system_prompt_block(self):
        palette = ["#FF0000", "#00FF00"]
        prompt = build_system_prompt("a red apple", palette, 16, "block")

        assert "a red apple" in prompt
        assert "16x16" in prompt
        assert "0: #FF0000" in prompt
        assert "1: #00FF00" in prompt
        assert "BLOCK TILE" in prompt
        assert "draw_pixel" in prompt
        assert "finish()" in prompt

    def test_build_system_prompt_icon(self):
        palette = ["#FF0000"]
        prompt = build_system_prompt("sword", palette, 8, "icon")

        assert "sword" in prompt
        assert "ITEM ICON" in prompt

    def test_build_system_prompt_entity(self):
        palette = ["#FF0000"]
        prompt = build_system_prompt("hero", palette, 32, "entity")

        assert "CHARACTER SPRITE" in prompt

    def test_build_system_prompt_autotile(self):
        palette = ["#FF0000"]
        prompt = build_system_prompt("wall", palette, 16, "autotile")

        assert "AUTOTILE" in prompt

    def test_build_continuation_prompt(self):
        canvas = Canvas(4, ["#FF0000"])
        canvas.pixels = [[0, 0, 0, 0], [0, 1, 1, 0], [0, 1, 1, 0], [0, 0, 0, 0]]
        prompt = build_continuation_prompt("a red circle", canvas)

        assert "red circle" in prompt
        assert "CURRENT CANVAS STATE" in prompt
        assert "make changes" in prompt


class TestToolParsing:
    def test_parse_draw_pixel(self):
        response = "I'll draw a pixel at (3, 5) with color 1. draw_pixel(x=3, y=5, color=1)"
        calls = parse_tool_calls(response)

        assert len(calls) == 1
        assert calls[0]["tool"] == "draw_pixel"
        assert calls[0]["args"]["x"] == 3
        assert calls[0]["args"]["y"] == 5
        assert calls[0]["args"]["color"] == 1

    def test_parse_fill_rect(self):
        response = "fill_rect(x1=2, y1=3, x2=5, y2=7, color=2)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "fill_rect"
        assert calls[0]["args"]["x1"] == 2
        assert calls[0]["args"]["color"] == 2

    def test_parse_draw_line(self):
        response = "draw_line(x1=0, y1=0, x2=10, y2=10, color=1)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "draw_line"
        assert calls[0]["args"]["x1"] == 0

    def test_parse_draw_circle(self):
        response = "draw_circle(cx=5, cy=5, radius=3, color=1, fill=True)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "draw_circle"
        assert calls[0]["args"]["cx"] == 5
        assert calls[0]["args"]["fill"] == True

    def test_parse_draw_circle_no_fill(self):
        response = "draw_circle(cx=5, cy=5, radius=3, color=1)"
        calls = parse_tool_calls(response)

        # Default fill is True
        assert calls[0]["args"]["fill"] == True

    def test_parse_draw_ellipse(self):
        response = "draw_ellipse(cx=4, cy=4, rx=2, ry=1, color=1, fill=False)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "draw_ellipse"
        assert calls[0]["args"]["rx"] == 2
        assert calls[0]["args"]["fill"] == False

    def test_parse_draw_triangle(self):
        response = "draw_triangle(x1=0, y1=0, x2=10, y2=0, x3=5, y3=10, color=1)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "draw_triangle"
        assert calls[0]["args"]["x3"] == 5

    def test_parse_draw_rotated_rect(self):
        response = "draw_rotated_rect(cx=5, cy=5, width=4, height=2, angle=45.0, color=1)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "draw_rotated_rect"
        assert calls[0]["args"]["angle"] == 45.0

    def test_parse_noise_fill_rect(self):
        response = "noise_fill_rect(x1=0, y1=0, x2=7, y2=7, colors=[0,1], seed=42, scale=1.5)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "noise_fill_rect"
        assert calls[0]["args"]["colors"] == [0, 1]
        assert calls[0]["args"]["seed"] == 42

    def test_parse_voronoi_fill(self):
        response = "voronoi_fill(x1=0, y1=0, x2=7, y2=7, colors=[0,1,2], num_cells=6)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "voronoi_fill"
        assert calls[0]["args"]["num_cells"] == 6

    def test_parse_view_canvas(self):
        response = "Let me check the canvas view_canvas()"
        calls = parse_tool_calls(response)

        assert len(calls) == 1
        assert calls[0]["tool"] == "view_canvas"

    def test_parse_get_pixel(self):
        response = "get_pixel(x=5, y=5)"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "get_pixel"
        assert calls[0]["args"]["x"] == 5

    def test_parse_finish(self):
        response = "I'm done. finish()"
        calls = parse_tool_calls(response)

        assert calls[0]["tool"] == "finish"

    def test_parse_multiple_tools(self):
        response = """
        draw_pixel(x=0, y=0, color=1)
        draw_pixel(x=1, y=0, color=1)
        fill_rect(x1=2, y1=2, x2=5, y2=5, color=0)
        view_canvas()
        finish()
        """
        calls = parse_tool_calls(response)

        assert len(calls) == 5
        assert calls[0]["tool"] == "draw_pixel"
        assert calls[3]["tool"] == "view_canvas"
        assert calls[4]["tool"] == "finish"

    def test_parse_negative_color(self):
        response = "draw_pixel(x=0, y=0, color=-1)"
        calls = parse_tool_calls(response)

        assert calls[0]["args"]["color"] == -1


class TestExecuteTool:
    def test_execute_draw_pixel(self):
        canvas = Canvas(4, ["#FF0000", "#00FF00"])
        result = execute_tool(canvas, "draw_pixel", {"x": 2, "y": 2, "color": 1})

        assert canvas.pixels[2][2] == 1
        assert "Set (2,2) to 1" in result

    def test_execute_fill_rect(self):
        canvas = Canvas(8, ["#FF0000"])
        result = execute_tool(canvas, "fill_rect", {"x1": 1, "y1": 1, "x2": 3, "y2": 3, "color": 0})

        assert canvas.pixels[1][1] == 0
        assert canvas.pixels[3][3] == 0

    def test_execute_draw_line(self):
        canvas = Canvas(10, ["#FF0000"])
        execute_tool(canvas, "draw_line", {"x1": 0, "y1": 0, "x2": 9, "y2": 9, "color": 0})

        assert canvas.pixels[0][0] == 0
        assert canvas.pixels[9][9] == 0

    def test_execute_draw_circle(self):
        canvas = Canvas(16, ["#FF0000"])
        count = execute_tool(
            canvas, "draw_circle", {"cx": 8, "cy": 8, "radius": 3, "color": 0, "fill": True}
        )

        assert count > 0
        assert canvas.pixels[8][8] == 0

    def test_execute_view_canvas(self):
        canvas = Canvas(4, ["#FF0000"])
        canvas.pixels = [[0, 0, 0, 0], [0, 1, 1, 0], [0, 1, 1, 0], [0, 0, 0, 0]]
        result = execute_tool(canvas, "view_canvas", {})

        assert "COLOR USAGE" in result
        assert "Filled:" in result

    def test_execute_get_pixel(self):
        canvas = Canvas(4, ["#FF0000"])
        canvas.pixels = [[0, 1], [2, 3]]
        result = execute_tool(canvas, "get_pixel", {"x": 1, "y": 0})

        assert "1" in result

    def test_execute_finish(self):
        canvas = Canvas(4, ["#FF0000"])
        result = execute_tool(canvas, "finish", {})

        assert result == "FINISHED"

    def test_execute_unknown_tool(self):
        canvas = Canvas(4, ["#FF0000"])
        result = execute_tool(canvas, "unknown_tool", {})

        assert "Unknown tool" in result


class TestSession:
    def test_session_creation(self):
        canvas = Canvas(4, ["#FF0000"])
        messages = [{"role": "system", "content": "test"}]
        session = Session(1, canvas, messages, "test prompt")

        assert session.gen_id == 1
        assert session.canvas == canvas
        assert session.messages == messages
        assert session.original_prompt == "test prompt"
