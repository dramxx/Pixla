import re
import httpx
from typing import Optional, Callable
from app.services.canvas import Canvas
from app.config import get_settings
from app.services.constants import SPRITE_TYPE_HINTS
from app.utils.logging import agent_logger, log_operation


TOOL_DESCRIPTIONS = """
You have tools to draw pixels on a canvas. Use them to create pixel art.

TOOLS:
- draw_pixel(x, y, color): Set single pixel at (x,y) to palette color index. Use -1 for transparent.
- fill_rect(x1, y1, x2, y2, color): Fill rectangle from (x1,y1) to (x2,y2) inclusive.
- fill_row(y, x_start, x_end, color): Fill horizontal row at y from x_start to x_end.
- fill_column(x, y_start, y_end, color): Fill vertical column at x from y_start to y_end.
- draw_line(x1, y1, x2, y2, color): Draw 1-pixel-wide line from (x1,y1) to (x2,y2).
- draw_circle(cx, cy, radius, color, fill): Draw circle. fill=true for solid.
- draw_ellipse(cx, cy, rx, ry, color, fill): Draw ellipse. rx/ry = radii.
- draw_triangle(x1, y1, x2, y2, x3, y3, color): Draw filled triangle with 3 corners.
- draw_rotated_rect(cx, cy, width, height, angle, color): Draw rotated rectangle (angle in degrees).
- noise_fill_rect(x1, y1, x2, y2, colors, seed, scale): Fill rectangle with noise-distributed colors.
- noise_fill_circle(cx, cy, radius, colors, seed): Fill circle with noise colors.
- voronoi_fill(x1, y1, x2, y2, colors, num_cells, seed): Fill with Voronoi cell pattern.
- view_canvas(): View current canvas state - returns grid, color usage, and rendered image.
- get_pixel(x, y): Get palette index at (x,y).
- finish(): Call when the sprite is complete.
"""


def build_system_prompt(prompt: str, palette: list[str], size: int, sprite_type: str) -> str:
    palette_desc = "\n".join(f"  {i}: {c}" for i, c in enumerate(palette))
    type_hint = SPRITE_TYPE_HINTS.get(sprite_type, SPRITE_TYPE_HINTS["block"])

    return f"""You are a pixel artist working on a {size}x{size} canvas.
You have tools to draw pixels, fill rectangles, draw shapes, add texture, and view your work.

SUBJECT TO DRAW: {prompt}

PALETTE (color indices - use these numbers):
{palette_desc}
Use -1 for transparent pixels.

{type_hint}

{TOOL_DESCRIPTIONS}

WORKFLOW:
1. Start by filling the base shape with fill_rect or shapes
2. Add texture with noise_fill_rect or voronoi_fill for natural variation
3. Add detail with individual pixels
4. Use view_canvas to check your progress
5. Call finish when the sprite looks complete

IMPORTANT:
- You have LIMITED iterations - do NOT keep drawing endlessly
- After 2-3 drawing actions, check with view_canvas and decide if done
- If canvas has meaningful content, CALL finish() - don't over-detail
- "Done" means recognizable sprite, not perfection
- ITERATION LIMIT: If you call finish with an error (canvas empty), you must draw something first

Remember: (0,0) is top-left, ({size - 1},{size - 1}) is bottom-right."""


def build_continuation_prompt(original_prompt: str, canvas: Canvas) -> str:
    grid = canvas.to_grid_string()
    return f"""The user wants you to make changes to the current sprite.

ORIGINAL REQUEST: {original_prompt}

CURRENT CANVAS STATE:
{grid}

Use the canvas tools to make the requested changes. Call view_canvas to check progress, then call finish when done."""


def parse_tool_calls(response: str) -> list[dict]:
    """Parse tool calls from LLM response using regex."""
    # First try to extract from markdown code blocks
    # Look for content between ```python or ``` and ```
    code_block_match = re.search(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)
    if code_block_match:
        response = code_block_match.group(1)

    # Also look for tool calls after "Output:" or "Result:" prefix
    output_match = re.search(r"(?:Output|Result|Answer):\s*(.*)", response, re.DOTALL)
    if output_match:
        response = output_match.group(1)

    tool_patterns = {
        "draw_pixel": r"draw_pixel\(x=(\d+),\s*y=(\d+),\s*color=(-?\d+)\)",
        "fill_rect": r"fill_rect\(x1=(\d+),\s*y1=(\d+),\s*x2=(\d+),\s*y2=(\d+),\s*color=(-?\d+)\)",
        "fill_row": r"fill_row\(y=(\d+),\s*x_start=(\d+),\s*x_end=(\d+),\s*color=(-?\d+)\)",
        "fill_column": r"fill_column\(x=(\d+),\s*y_start=(\d+),\s*y_end=(\d+),\s*color=(-?\d+)\)",
        "draw_line": r"draw_line\(x1=(\d+),\s*y1=(\d+),\s*x2=(\d+),\s*y2=(\d+),\s*color=(-?\d+)\)",
        "draw_circle": r"draw_circle\(cx=(\d+),\s*cy=(\d+),\s*radius=(\d+),\s*color=(-?\d+)(?:,\s*fill=(True|False))?\)",
        "draw_ellipse": r"draw_ellipse\(cx=(\d+),\s*cy=(\d+),\s*rx=(\d+),\s*ry=(\d+),\s*color=(-?\d+)(?:,\s*fill=(True|False))?\)",
        "draw_triangle": r"draw_triangle\(x1=(\d+),\s*y1=(\d+),\s*x2=(\d+),\s*y2=(\d+),\s*x3=(\d+),\s*y3=(\d+),\s*color=(-?\d+)\)",
        "draw_rotated_rect": r"draw_rotated_rect\(cx=(\d+),\s*cy=(\d+),\s*width=(\d+),\s*height=(\d+),\s*angle=(-?\d+\.?\d*),\s*color=(-?\d+)\)",
        "noise_fill_rect": r"noise_fill_rect\(x1=(\d+),\s*y1=(\d+),\s*x2=(\d+),\s*y2=(\d+),\s*colors=\[([\d,\s]+)\](?:,\s*seed=(\d+))?(?:,\s*scale=(\d+\.?\d*))?\)",
        "noise_fill_circle": r"noise_fill_circle\(cx=(\d+),\s*cy=(\d+),\s*radius=(\d+),\s*colors=\[([\d,\s]+)\](?:,\s*seed=(\d+))?\)",
        "voronoi_fill": r"voronoi_fill\(x1=(\d+),\s*y1=(\d+),\s*x2=(\d+),\s*y2=(\d+),\s*colors=\[([\d,\s]+)\](?:,\s*num_cells=(\d+))?(?:,\s*seed=(\d+))?\)",
        "view_canvas": r"view_canvas\(\)",
        "get_pixel": r"get_pixel\(x=(\d+),\s*y=(\d+)\)",
        "finish": r"finish\(\)",
    }

    calls = []
    for tool_name, pattern in tool_patterns.items():
        for match in re.finditer(pattern, response):
            args = match.groups()
            if tool_name == "draw_pixel":
                calls.append(
                    {
                        "tool": "draw_pixel",
                        "args": {
                            "x": int(args[0]),
                            "y": int(args[1]),
                            "color": int(args[2]),
                        },
                    }
                )
            elif tool_name == "fill_rect":
                calls.append(
                    {
                        "tool": "fill_rect",
                        "args": {
                            "x1": int(args[0]),
                            "y1": int(args[1]),
                            "x2": int(args[2]),
                            "y2": int(args[3]),
                            "color": int(args[4]),
                        },
                    }
                )
            elif tool_name == "fill_row":
                calls.append(
                    {
                        "tool": "fill_row",
                        "args": {
                            "y": int(args[0]),
                            "x_start": int(args[1]),
                            "x_end": int(args[2]),
                            "color": int(args[3]),
                        },
                    }
                )
            elif tool_name == "fill_column":
                calls.append(
                    {
                        "tool": "fill_column",
                        "args": {
                            "x": int(args[0]),
                            "y_start": int(args[1]),
                            "y_end": int(args[2]),
                            "color": int(args[3]),
                        },
                    }
                )
            elif tool_name == "draw_line":
                calls.append(
                    {
                        "tool": "draw_line",
                        "args": {
                            "x1": int(args[0]),
                            "y1": int(args[1]),
                            "x2": int(args[2]),
                            "y2": int(args[3]),
                            "color": int(args[4]),
                        },
                    }
                )
            elif tool_name == "draw_circle":
                fill = args[5] == "True" if len(args) > 5 and args[5] else True
                calls.append(
                    {
                        "tool": "draw_circle",
                        "args": {
                            "cx": int(args[0]),
                            "cy": int(args[1]),
                            "radius": int(args[2]),
                            "color": int(args[3]),
                            "fill": fill,
                        },
                    }
                )
            elif tool_name == "draw_ellipse":
                fill = args[5] == "True" if len(args) > 5 and args[5] else True
                calls.append(
                    {
                        "tool": "draw_ellipse",
                        "args": {
                            "cx": int(args[0]),
                            "cy": int(args[1]),
                            "rx": int(args[2]),
                            "ry": int(args[3]),
                            "color": int(args[4]),
                            "fill": fill,
                        },
                    }
                )
            elif tool_name == "draw_triangle":
                calls.append(
                    {
                        "tool": "draw_triangle",
                        "args": {
                            "x1": int(args[0]),
                            "y1": int(args[1]),
                            "x2": int(args[2]),
                            "y2": int(args[3]),
                            "x3": int(args[4]),
                            "y3": int(args[5]),
                            "color": int(args[6]),
                        },
                    }
                )
            elif tool_name == "draw_rotated_rect":
                calls.append(
                    {
                        "tool": "draw_rotated_rect",
                        "args": {
                            "cx": int(args[0]),
                            "cy": int(args[1]),
                            "width": int(args[2]),
                            "height": int(args[3]),
                            "angle": float(args[4]),
                            "color": int(args[5]),
                        },
                    }
                )
            elif tool_name == "noise_fill_rect":
                colors = [int(x.strip()) for x in args[4].split(",")]
                seed = int(args[5]) if len(args) > 5 and args[5] else 42
                scale = float(args[6]) if len(args) > 6 and args[6] else 1.0
                calls.append(
                    {
                        "tool": "noise_fill_rect",
                        "args": {
                            "x1": int(args[0]),
                            "y1": int(args[1]),
                            "x2": int(args[2]),
                            "y2": int(args[3]),
                            "colors": colors,
                            "seed": seed,
                            "scale": scale,
                        },
                    }
                )
            elif tool_name == "noise_fill_circle":
                colors = [int(x.strip()) for x in args[3].split(",")]
                seed = int(args[4]) if len(args) > 4 and args[4] else 42
                calls.append(
                    {
                        "tool": "noise_fill_circle",
                        "args": {
                            "cx": int(args[0]),
                            "cy": int(args[1]),
                            "radius": int(args[2]),
                            "colors": colors,
                            "seed": seed,
                        },
                    }
                )
            elif tool_name == "voronoi_fill":
                colors = [int(x.strip()) for x in args[4].split(",")]
                num_cells = int(args[5]) if len(args) > 5 and args[5] else 8
                seed = int(args[6]) if len(args) > 6 and args[6] else 42
                calls.append(
                    {
                        "tool": "voronoi_fill",
                        "args": {
                            "x1": int(args[0]),
                            "y1": int(args[1]),
                            "x2": int(args[2]),
                            "y2": int(args[3]),
                            "colors": colors,
                            "num_cells": num_cells,
                            "seed": seed,
                        },
                    }
                )
            elif tool_name == "view_canvas":
                calls.append({"tool": "view_canvas", "args": {}})
            elif tool_name == "get_pixel":
                calls.append(
                    {
                        "tool": "get_pixel",
                        "args": {"x": int(args[0]), "y": int(args[1])},
                    }
                )
            elif tool_name == "finish":
                calls.append({"tool": "finish", "args": {}})

    return calls


def execute_tool(canvas: Canvas, tool_name: str, args: dict) -> str:
    """Execute a tool on the canvas and return the result."""

    if tool_name == "draw_pixel":
        return canvas.set_pixel(args["x"], args["y"], args["color"])
    elif tool_name == "fill_rect":
        return canvas.fill_rect(args["x1"], args["y1"], args["x2"], args["y2"], args["color"])
    elif tool_name == "fill_row":
        return canvas.fill_row(args["y"], args["x_start"], args["x_end"], args["color"])
    elif tool_name == "fill_column":
        return canvas.fill_column(args["x"], args["y_start"], args["y_end"], args["color"])
    elif tool_name == "draw_line":
        return canvas.draw_line(args["x1"], args["y1"], args["x2"], args["y2"], args["color"])
    elif tool_name == "draw_circle":
        return canvas.draw_circle(
            args["cx"],
            args["cy"],
            args["radius"],
            args["color"],
            args.get("fill", True),
        )
    elif tool_name == "draw_ellipse":
        return canvas.draw_ellipse(
            args["cx"],
            args["cy"],
            args["rx"],
            args["ry"],
            args["color"],
            args.get("fill", True),
        )
    elif tool_name == "draw_triangle":
        return canvas.draw_triangle(
            args["x1"],
            args["y1"],
            args["x2"],
            args["y2"],
            args["x3"],
            args["y3"],
            args["color"],
        )
    elif tool_name == "draw_rotated_rect":
        return canvas.draw_rotated_rect(
            args["cx"],
            args["cy"],
            args["width"],
            args["height"],
            args["angle"],
            args["color"],
        )
    elif tool_name == "noise_fill_rect":
        return canvas.fill_noise(
            args["x1"],
            args["y1"],
            args["x2"],
            args["y2"],
            args["colors"],
            args.get("seed", 42),
            args.get("scale", 1.0),
        )
    elif tool_name == "noise_fill_circle":
        return canvas.fill_noise_circle(
            args["cx"], args["cy"], args["radius"], args["colors"], args.get("seed", 42)
        )
    elif tool_name == "voronoi_fill":
        return canvas.fill_voronoi(
            args["x1"],
            args["y1"],
            args["x2"],
            args["y2"],
            args["colors"],
            args.get("num_cells", 8),
            args.get("seed", 42),
        )
    elif tool_name == "view_canvas":
        return canvas.view_canvas()
    elif tool_name == "get_pixel":
        v = canvas.get_pixel(args["x"], args["y"])
        name = canvas.palette[v] if 0 <= v < len(canvas.palette) else "transparent"
        return f"({args['x']},{args['y']}) = {v} ({name})"
    elif tool_name == "finish":
        return canvas.finish()

    return f"Unknown tool: {tool_name}"


class Session:
    """Agent session for a single generation - maintains conversation history and canvas."""

    def __init__(self, gen_id: int, canvas: Canvas, messages: list[dict], original_prompt: str):
        self.gen_id = gen_id
        self.canvas = canvas
        self.messages = messages
        self.original_prompt = original_prompt


_sessions: dict[int, Session] = {}


def cleanup_session(gen_id: int):
    """Remove session when done."""
    _sessions.pop(gen_id, None)


def cleanup_agent():
    """Close agent HTTP client and reset instance."""
    global _agent_instance
    if _agent_instance is not None:
        _agent_instance.close()
        _agent_instance = None


class LocalAgent:
    """Agent that uses local LLM (llama-server) for pixel art generation."""

    def __init__(self, llm_url: str, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        self.llm_url = llm_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.http_client = httpx.Client(timeout=30.0)

    def check_connectivity(self) -> tuple[bool, str]:
        """Check if LLM server is reachable and responding.

        Returns:
            Tuple of (is_available, error_message)
            - (True, "") if server is reachable
            - (False, "error details") if unreachable
        """
        try:
            log_operation(
                agent_logger, "LLM connectivity check", details=f"checking {self.llm_url}"
            )
            response = self.http_client.get(
                f"{self.llm_url}/v1/models",
                timeout=10.0,
            )
            if response.status_code == 200:
                log_operation(
                    agent_logger,
                    "LLM connectivity check",
                    success=True,
                    details="LLM server is ready",
                )
                return (True, "")
            else:
                error_msg = f"LLM server returned status {response.status_code}"
                log_operation(
                    agent_logger, "LLM connectivity check", success=False, details=error_msg
                )
                return (False, error_msg)
        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to LLM at {self.llm_url}: {e}"
            log_operation(agent_logger, "LLM connectivity check", success=False, error=e)
            return (False, error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"LLM server timed out: {e}"
            log_operation(agent_logger, "LLM connectivity check", success=False, error=e)
            return (False, error_msg)
        except Exception as e:
            error_msg = f"LLM connectivity check failed: {type(e).__name__}: {e}"
            log_operation(agent_logger, "LLM connectivity check", success=False, error=e)
            return (False, error_msg)

    def chat(self, messages: list[dict]) -> str:
        """Send a chat request to local LLM."""
        try:
            # Log what we're sending (truncated)
            msg_summary = f"model={self.model}, messages={len(messages)}"
            if messages:
                # Log first message (usually system prompt length) and last user message
                last_user = next(
                    (m["content"][:200] for m in reversed(messages) if m["role"] == "user"), ""
                )
                msg_summary += f", last_msg: {last_user[:100]}..."

            log_operation(
                agent_logger,
                "LLM chat request",
                details=msg_summary,
            )
            response = self.http_client.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract usage info if available
            usage_info = ""
            if "usage" in data:
                usage = data["usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                usage_info = f", tokens={total_tokens}(p={prompt_tokens},c={completion_tokens})"

            content = data["choices"][0]["message"]["content"]

            # Log LLM response (truncated for readability)
            response_preview = (
                content[:300].replace("\n", " ") + "..."
                if len(content) > 300
                else content.replace("\n", " ")
            )
            log_operation(
                agent_logger,
                "LLM response",
                details=f"{response_preview}{usage_info}",
            )

            return content
        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to LLM: {e}"
            log_operation(agent_logger, "LLM chat request", success=False, error=e)
            raise ConnectionError(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"LLM request timed out: {e}"
            log_operation(agent_logger, "LLM chat request", success=False, error=e)
            raise TimeoutError(error_msg) from e
        except httpx.HTTPStatusError as e:
            log_operation(
                agent_logger,
                "LLM chat request",
                success=False,
                details=f"HTTP {e.response.status_code}",
            )
            raise RuntimeError(
                f"LLM returned error: {e.response.status_code} - {e.response.text[:200]}"
            ) from e
        except Exception as e:
            log_operation(agent_logger, "LLM chat request", success=False, error=e)
            raise RuntimeError(f"LLM request failed: {type(e).__name__}: {e}") from e

    def run(
        self,
        gen_id: int,
        prompt: str,
        palette: list[str],
        size: int,
        sprite_type: str = "block",
        max_iterations: int = 40,
        existing_pixels: Optional[list[list[int]]] = None,
        on_step: Optional[Callable[[int, str, str], None]] = None,
        reference_image_b64: Optional[str] = None,
    ) -> Canvas:
        """Run the agent to generate pixel art (initial generation).

        Args:
            reference_image_b64: Optional base64 encoded reference image to include in prompt
        """
        log_operation(
            agent_logger,
            "Agent run started",
            details=f"gen_id={gen_id}, size={size}x{size}, max_iterations={max_iterations}",
        )

        # Check LLM connectivity before starting
        is_available, error_msg = self.check_connectivity()
        if not is_available:
            log_operation(
                agent_logger, "Agent run failed - LLM unavailable", success=False, details=error_msg
            )
            raise ConnectionError(f"LLM server unavailable: {error_msg}")

        canvas = Canvas(size, palette, existing_pixels)

        # Build system prompt - include reference if provided
        if reference_image_b64:
            system_prompt = f"""A reference concept image is provided. Match its shapes, colors, and composition as closely as possible in pixel art form.

Reference image (base64 PNG): data:image/png;base64,{reference_image_b64}

{build_system_prompt(prompt, palette, size, sprite_type)}"""
        else:
            system_prompt = build_system_prompt(prompt, palette, size, sprite_type)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Generate pixel art for: "{prompt}"

STRICT INSTRUCTIONS - USE THIS EXACT FORMAT:

CORRECT (will be parsed):
- fill_rect(x1=16, y1=32, x2=48, y2=48, color=2)
- draw_circle(cx=32, cy=32, radius=8, color=1, fill=True)
- view_canvas()
- finish()

WRONG (will be ignored):
- "I'll draw a rectangle" 
- "```python\nfill_rect(...)\n```"
- Any explanation text before the tool call

You MUST output ONLY the tool call, no explanation, no markdown, no code blocks.
Start with a drawing tool now.""",
            },
        ]

        _sessions[gen_id] = Session(gen_id, canvas, messages, prompt)

        result = self._run_loop(gen_id, messages, canvas, max_iterations, on_step)

        log_operation(agent_logger, "Agent run completed", success=True, details=f"gen_id={gen_id}")

        # Clean up session to prevent memory leak
        _sessions.pop(gen_id, None)

        return result

    def continue_session(
        self,
        gen_id: int,
        message: str,
        on_step: Optional[Callable[[int, str, str], None]] = None,
    ) -> Canvas:
        """Continue an existing agent session (for edits)."""

        if gen_id not in _sessions:
            raise ValueError(f"No session found for generation {gen_id}")

        session = _sessions[gen_id]
        canvas = session.canvas

        continuation_prompt = build_continuation_prompt(session.original_prompt, canvas)

        session.messages.append(
            {
                "role": "user",
                "content": f"{continuation_prompt}\n\nUSER REQUEST: {message}",
            }
        )

        return self._run_loop(gen_id, session.messages, canvas, 40, on_step)

    def _run_loop(
        self,
        gen_id: int,
        messages: list[dict],
        canvas: Canvas,
        max_iterations: int,
        on_step: Optional[Callable[[int, str, str], None]],
    ) -> Canvas:
        """Internal loop for running agent iterations."""

        # Keep message history bounded to avoid context overflow
        # Keep: system prompt + last N conversation turns
        MAX_MESSAGES = 10  # About 20 message entries (user + assistant pairs)

        # Track empty finish attempts to prevent infinite loops
        empty_finish_count = 0
        MAX_EMPTY_FINISH = 3

        iteration = 0

        while iteration < max_iterations:
            if on_step:
                on_step(iteration, "thinking", "Getting LLM response...")

            response = self.chat(messages)
            messages.append({"role": "assistant", "content": response})

            # Log full LLM response to DB for frontend display
            if on_step:
                on_step(iteration, "llm_response", response)

            tool_calls = parse_tool_calls(response)

            if not tool_calls:
                messages.append(
                    {
                        "role": "user",
                        "content": "Please use a tool. Call view_canvas to see the canvas, then continue drawing or finish.",
                    }
                )
                if on_step:
                    on_step(iteration, "warning", "No tool calls found in LLM response")
                continue

            for call in tool_calls:
                tool_name = call["tool"]
                tool_args = call["args"]

                if on_step:
                    on_step(iteration, "tool_call", f"{tool_name}({tool_args})")

                result = execute_tool(canvas, tool_name, tool_args)

                if on_step:
                    on_step(iteration, "tool_result", result)

                messages.append({"role": "user", "content": f"Tool {tool_name} result: {result}"})

                if tool_name == "finish":
                    # Check if finish returned an error (empty canvas)
                    if result.startswith("ERROR:"):
                        empty_finish_count += 1
                        if empty_finish_count >= MAX_EMPTY_FINISH:
                            # Too many empty finish attempts - force a simple fill
                            on_step(
                                iteration,
                                "warning",
                                "Too many empty finish attempts. Forcing basic fill...",
                            )
                            canvas.fill_rect(0, 0, canvas.size - 1, canvas.size - 1, 0)
                            return canvas
                        # Don't return - continue to draw more
                        on_step(iteration, "warning", f"Finish rejected: {result}. Continuing...")
                        messages.append(
                            {
                                "role": "user",
                                "content": "You cannot finish with an empty canvas. Use fill_rect, draw_circle, or other tools to draw the sprite first. Keep drawing until canvas has content, then call finish().",
                            }
                        )
                        continue
                    return canvas

            # Trim message history to prevent context overflow
            if len(messages) > MAX_MESSAGES + 1:  # +1 for system message
                # Keep system message, trim to recent messages
                system_msg = messages[0]  # system prompt
                recent = messages[-(MAX_MESSAGES):]
                messages = [system_msg] + recent

            iteration += 1

        return canvas

    def close(self):
        self.http_client.close()


_agent_instance: Optional[LocalAgent] = None


def get_agent() -> LocalAgent:
    """Get or create agent instance."""
    global _agent_instance
    if _agent_instance is None:
        settings = get_settings()
        llm_url = f"http://{settings.llm_host}:{settings.llm_port}"
        _agent_instance = LocalAgent(
            llm_url=llm_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    return _agent_instance


def get_session(gen_id: int) -> Optional[Session]:
    """Get an existing session."""
    return _sessions.get(gen_id)
