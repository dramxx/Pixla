from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, field_validator, model_validator
from PIL import Image
from typing import Optional, List
from enum import Enum
import json
import uuid
import asyncio
from pathlib import Path

from app.models import GenerationStatus
from app.services.quantization import quantize_image_to_palette, pixels_to_image, detect_background
from app.services.agent import get_agent, get_session, cleanup_session
from app.services.autotile import generate_tileset
from app.utils.logging import pipeline_logger, log_operation

router = APIRouter()

_gen_events: dict[int, asyncio.Event] = {}


def _get_gen_event(gen_id: int) -> asyncio.Event:
    if gen_id not in _gen_events:
        _gen_events[gen_id] = asyncio.Event()
    return _gen_events[gen_id]


def _notify_gen_update(gen_id: int):
    if gen_id in _gen_events:
        _gen_events[gen_id].set()


def _clear_gen_event(gen_id: int):
    if gen_id in _gen_events:
        _gen_events[gen_id].clear()
        del _gen_events[gen_id]


class SpriteType(str, Enum):
    BLOCK = "block"
    ICON = "icon"
    ENTITY = "entity"
    AUTOTILE = "autotile"


class CreateGenerationRequest(BaseModel):
    prompt: str
    colors: List[str]
    size: int = 16
    sprite_type: SpriteType = SpriteType.BLOCK
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    loras: Optional[List[dict]] = None
    num_inference_steps: Optional[int] = None
    guidance_scale: Optional[float] = None
    reference_only: bool = False
    use_agent: bool = True

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v < 4 or v > 128:
            raise ValueError("size must be between 4 and 128")
        return v

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, v):
        for color in v:
            if not color.startswith("#") or len(color) != 7:
                raise ValueError(f"Invalid color format: {color}")
            try:
                int(color[1:], 16)
            except ValueError:
                raise ValueError(f"Invalid color: {color}")
        return v


class ChatRequest(BaseModel):
    message: str
    region_x1: Optional[int] = None
    region_y1: Optional[int] = None
    region_x2: Optional[int] = None
    region_y2: Optional[int] = None
    region_description: Optional[str] = None

    @field_validator("region_x1", "region_y1", "region_x2", "region_y2")
    @classmethod
    def validate_region_coords(cls, v, info):
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} must be >= 0")
        if v is not None and v > 512:
            raise ValueError(f"{info.field_name} must be <= 512")
        return v

    @model_validator(mode="after")
    def validate_region_order(self):
        # Ensure x1 < x2 and y1 < y2 when both are provided
        if self.region_x1 is not None and self.region_x2 is not None:
            if self.region_x1 >= self.region_x2:
                raise ValueError("region_x1 must be less than region_x2")
        if self.region_y1 is not None and self.region_y2 is not None:
            if self.region_y1 >= self.region_y2:
                raise ValueError("region_y1 must be less than region_y2")
        return self


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/generations")
async def create_generation(req: CreateGenerationRequest, request: Request):
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.create_generation(
        prompt=req.prompt,
        colors=req.colors,
        size=req.size,
        sprite_type=req.sprite_type,
        system_prompt=req.system_prompt,
        model=req.model,
    )

    log_operation(
        pipeline_logger,
        "Generation started",
        details=f"gen_id={gen.id}, prompt={req.prompt[:30]}...",
    )

    try:
        db.update_generation_status(gen.id, GenerationStatus.GENERATING)
        _notify_gen_update(gen.id)

        references_dir = storage_path / "references"
        references_dir.mkdir(parents=True, exist_ok=True)

        reference_id = f"ref_{gen.id}_{uuid.uuid4().hex[:8]}.png"
        reference_path = references_dir / reference_id

        from app.services.diffusion import get_diffusion, unload_diffusion

        # Step 1: Generate reference image with diffusion
        log_operation(pipeline_logger, "Step 1/3: Generating reference image", details=f"size=512")

        diffusion = get_diffusion(req.model)
        reference = diffusion.generate_pixel_art_reference(
            prompt=req.prompt,
            sprite_type=req.sprite_type.value,
            target_size=512,
            loras=req.loras,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
        )

        # Downscale to target size using Lanczos for quality
        if req.size != 512:
            reference = reference.resize((req.size, req.size), Image.LANCZOS)
        reference.save(reference_path)
        db.update_generation_reference(gen.id, str(reference_path))

        # Free GPU memory after generation
        unload_diffusion()

        log_operation(
            pipeline_logger,
            "Reference image generated",
            success=True,
            details=f"saved to {reference_path}",
        )

        if req.reference_only:
            db.update_generation_status(gen.id, GenerationStatus.COMPLETE)
            _notify_gen_update(gen.id)
            gen = db.get_generation(gen.id)
            gen.reference_path = str(reference_path)
            return gen

        # Step 2: LLM agent draws pixel-by-pixel
        log_operation(
            pipeline_logger,
            "Step 2/3: LLM agent drawing pixels",
            details=f"size={req.size}x{req.size}",
        )

        agent_used_llm = False
        fallback_reason = None

        try:
            agent = get_agent()

            import base64
            import io

            # Convert reference image to base64 for LLM
            ref_bytes = io.BytesIO()
            reference.save(ref_bytes, format="PNG")
            ref_bytes.seek(0)
            ref_b64 = base64.b64encode(ref_bytes.read()).decode()

            def on_step(iteration: int, step_type: str, message: str):
                db.add_log(gen.id, step_type, message)

            canvas = agent.run(
                gen_id=gen.id,
                prompt=req.prompt,
                palette=req.colors,
                size=req.size,
                sprite_type=req.sprite_type.value,
                max_iterations=40,
                on_step=on_step,
                reference_image_b64=ref_b64,
            )

            pixel_data = canvas.pixels
            pixel_data = detect_background(pixel_data)
            iterations = 40
            agent_used_llm = True

            log_operation(
                pipeline_logger,
                "LLM agent completed",
                success=True,
                details=f"iterations={iterations}",
            )

        except (ConnectionError, TimeoutError, RuntimeError) as e:
            # Only fallback to quantization on actual connectivity/auth failures
            # These are genuine LLM failures that can't be retried
            error_msg = f"LLM agent failed: {type(e).__name__}: {e}"
            log_operation(pipeline_logger, "LLM agent failed", success=False, details=error_msg)
            db.add_log(gen.id, "error", error_msg)

            # Fall back to quantization but make it visible
            fallback_reason = str(e)
            log_operation(pipeline_logger, "Falling back to quantization", details=fallback_reason)

            pixel_data = quantize_image_to_palette(reference, req.colors, req.size, dither=True)
            pixel_data = detect_background(pixel_data)
            iterations = 1
            agent_used_llm = False

        except Exception as e:
            # For other exceptions (including tool parsing failures), raise instead of silently falling back
            # This helps identify what's actually broken
            error_msg = f"Unexpected error: {type(e).__name__}: {e}"
            log_operation(
                pipeline_logger,
                "Unexpected error during generation",
                success=False,
                details=error_msg,
            )
            db.add_log(gen.id, "error", error_msg)
            raise

        db.update_generation_pixels(gen.id, pixel_data, iterations)

        # Step 3: Save final image
        log_operation(pipeline_logger, "Step 3/3: Saving final image")

        img = pixels_to_image(pixel_data, req.colors)

        # Scale up for download (pixel art should be viewable at desktop resolution)
        scale = 8
        scaled_size = req.size * scale
        img = img.resize((scaled_size, scaled_size), Image.NEAREST)

        output_dir = storage_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        image_id = f"gen_{gen.id}_{scaled_size}x{scaled_size}.png"
        img.save(output_dir / image_id)

        db.update_generation_image(gen.id, str(output_dir / image_id))
        db.update_generation_status(gen.id, GenerationStatus.COMPLETE)
        _notify_gen_update(gen.id)

        log_operation(
            pipeline_logger,
            "Generation complete",
            success=True,
            details=f"agent_used={agent_used_llm}, fallback={fallback_reason is not None}",
        )

    except Exception as e:
        log_operation(pipeline_logger, "Generation failed", success=False, error=e)
        db.update_generation_status(gen.id, GenerationStatus.ERROR, str(e))
        _notify_gen_update(gen.id)
        _clear_gen_event(gen.id)  # Clean up event to prevent memory leak
        # Return actual error to frontend instead of generic 500
        raise HTTPException(500, f"Generation failed: {str(e)}")

    return db.get_generation(gen.id)


@router.get("/generations")
async def list_generations(request: Request, limit: int = 50, offset: int = 0):
    db = request.app.state.db
    return db.list_generations(limit, offset)


@router.get("/generations/{gen_id}")
async def get_generation(gen_id: int, request: Request):
    db = request.app.state.db
    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")
    return gen


@router.get("/generations/{gen_id}/stream")
async def stream_generation(gen_id: int, request: Request):
    db = request.app.state.db
    event = _get_gen_event(gen_id)

    # Track last log index to only send new logs
    last_log_id = 0
    max_logs_per_message = 20

    async def event_generator():
        nonlocal last_log_id

        for _ in range(120):
            gen = db.get_generation(gen_id)

            # Get logs since last check
            logs = []
            if gen:
                all_logs = db.get_logs(gen_id)
                # Only get new logs (after last_log_id)
                new_logs = [l for l in all_logs if l["id"] > last_log_id]
                if new_logs:
                    logs = new_logs[-max_logs_per_message:]  # Last N logs
                    last_log_id = new_logs[-1]["id"]

            log_messages = [
                {"step": l["step"], "message": l["message"], "ts": l["created_at"][-8:]}
                for l in logs
            ]

            data = {
                "id": gen.id if gen else gen_id,
                "status": gen.status.value if gen else "unknown",
                "iterations": gen.iterations if gen else 0,
                "logs": log_messages,
            }

            yield f"data: {json.dumps(data)}\n\n"

            if gen and gen.status in [
                GenerationStatus.COMPLETE.value,
                GenerationStatus.ERROR.value,
            ]:
                _clear_gen_event(gen_id)
                break

            await event.wait(timeout=1.0)
            event.clear()

        _clear_gen_event(gen_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/generations/{gen_id}/download")
async def download_generation(gen_id: int, request: Request):
    db = request.app.state.db
    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")
    if not gen.image_path:
        raise HTTPException(400, "No image available")

    img_path = Path(gen.image_path)
    if not img_path.exists():
        raise HTTPException(404, "Image file not found")

    storage_path = Path(request.app.state.storage_path).resolve()
    if not img_path.resolve().is_relative_to(storage_path):
        raise HTTPException(400, "Invalid path")

    def iter_file():
        with open(img_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={img_path.name}"},
    )


@router.post("/generations/{gen_id}/edit")
async def edit_generation(gen_id: int, req: ChatRequest, request: Request):
    """Continue an existing generation with edit requests.

    Creates a new agent session with the existing pixel data as starting point.
    """
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")

    if not gen.pixel_data:
        raise HTTPException(400, "No pixel data to edit")

    try:
        db.update_generation_status(gen_id, GenerationStatus.GENERATING)
        _notify_gen_update(gen_id)

        def on_step(iteration: int, step_type: str, message: str):
            db.add_log(gen_id, step_type, message)

        # Import here to avoid circular imports
        from app.services.agent import get_agent, LocalAgent
        from app.services.canvas import Canvas

        agent = get_agent()

        # Create canvas with existing pixel data as starting point
        canvas = Canvas(gen.size, gen.colors, gen.pixel_data)

        # Build continuation prompt with current canvas state
        from app.services.agent import build_system_prompt, build_continuation_prompt

        system_prompt = build_system_prompt(
            prompt=gen.prompt, palette=gen.colors, size=gen.size, sprite_type=gen.sprite_type
        )

        continuation_prompt = build_continuation_prompt(gen.prompt, canvas)

        # Build region targeting info if provided
        region_instruction = ""
        if (
            req.region_x1 is not None
            and req.region_y1 is not None
            and req.region_x2 is not None
            and req.region_y2 is not None
        ):
            region_instruction = f"""FOCUS AREA: You MUST restrict your edits to the region from ({req.region_x1}, {req.region_y1}) to ({req.region_x2}, {req.region_y2}). Do NOT modify pixels outside this area unless specifically requested.
"""
        elif req.region_description:
            region_instruction = f"""FOCUS AREA: {req.region_description}. Keep your edits focused on this area.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Current canvas state loaded from previous generation.

{continuation_prompt}
{region_instruction}
USER REQUEST: {req.message}

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

You MUST output ONLY the tool call, no explanation, no markdown, no code blocks.""",
            },
        ]

        # Run the agent loop manually with the existing canvas
        iteration = 0
        max_iterations = 40
        max_empty_finish = 3  # Prevent infinite loops
        empty_finish_count = 0

        while iteration < max_iterations:
            on_step(iteration, "thinking", "Getting LLM response...")

            response = agent.chat(messages)
            messages.append({"role": "assistant", "content": response})

            from app.services.agent import parse_tool_calls, execute_tool

            tool_calls = parse_tool_calls(response)

            if not tool_calls:
                # Log what the LLM actually returned - critical for debugging edit mode
                on_step(
                    iteration,
                    "warning",
                    f"No tool calls parsed from edit output. Raw: {response[:300]}...",
                )
                messages.append(
                    {
                        "role": "user",
                        "content": "Please output ONLY a tool call in this exact format: fill_rect(x1=0, y1=0, x2=16, y2=16, color=0) or view_canvas() or finish(). Do NOT include any explanation or markdown.",
                    }
                )
                continue

            for call in tool_calls:
                tool_name = call["tool"]
                tool_args = call["args"]

                on_step(iteration, "tool_call", f"{tool_name}({tool_args})")

                result = execute_tool(canvas, tool_name, tool_args)

                on_step(iteration, "tool_result", result)

                messages.append({"role": "user", "content": f"Tool {tool_name} result: {result}"})

                if tool_name == "finish":
                    # Check if finish returned an error (empty canvas)
                    if result.startswith("ERROR:"):
                        empty_finish_count += 1
                        if empty_finish_count >= max_empty_finish:
                            on_step(
                                iteration,
                                "warning",
                                "Too many empty finish attempts. Saving current state.",
                            )
                            break
                        on_step(iteration, "warning", f"Finish rejected: {result}. Continuing...")
                        messages.append(
                            {
                                "role": "user",
                                "content": "You cannot finish with an empty canvas. Use fill_rect, draw_circle, or other tools to draw first. Keep drawing until canvas has content, then call finish().",
                            }
                        )
                        continue

                    pixel_data = canvas.pixels
                    db.update_generation_pixels(gen_id, pixel_data, gen.iterations + 1)

                    img = pixels_to_image(pixel_data, gen.colors)
                    output_dir = storage_path / "output"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    image_id = f"gen_{gen_id}_{gen.size}x{gen.size}.png"
                    img.save(output_dir / image_id)

                    db.update_generation_image(gen_id, str(output_dir / image_id))
                    db.update_generation_status(gen_id, GenerationStatus.COMPLETE)
                    _notify_gen_update(gen_id)

                    return db.get_generation(gen_id)

            iteration += 1

        # Max iterations reached - save current state
        pixel_data = canvas.pixels
        db.update_generation_pixels(gen_id, pixel_data, gen.iterations + 1)

        img = pixels_to_image(pixel_data, gen.colors)
        output_dir = storage_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        image_id = f"gen_{gen_id}_{gen.size}x{gen.size}.png"
        img.save(output_dir / image_id)

        db.update_generation_image(gen_id, str(output_dir / image_id))
        db.update_generation_status(gen_id, GenerationStatus.COMPLETE)
        _notify_gen_update(gen_id)

    except Exception as e:
        _clear_gen_event(gen_id)
        db.update_generation_status(gen_id, GenerationStatus.ERROR, str(e))
        _notify_gen_update(gen_id)
        raise HTTPException(500, str(e))

    return db.get_generation(gen_id)


class TilesetRequest(BaseModel):
    name: str


@router.post("/generations/{gen_id}/tileset")
async def generate_tileset(gen_id: int, req: TilesetRequest, request: Request):
    """Generate a 16-variant tileset from a block sprite."""
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")
    if not gen.pixel_data:
        raise HTTPException(400, "No pixel data")
    # sprite_type is stored as string in DB (e.g., "block", "icon")
    if gen.sprite_type != SpriteType.BLOCK.value:
        raise HTTPException(400, "Tileset only works with block sprites")

    variants = generate_tileset(gen.pixel_data, gen.colors, gen.size)

    tileset_dir = storage_path / "output" / "tilesets" / req.name
    tileset_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for mask in range(16):
        filename = f"{req.name}_{mask:02d}.png"
        variants[mask].save(tileset_dir / filename)
        files.append(filename)

    return {
        "name": req.name,
        "count": len(files),
        "files": files,
    }


@router.get("/generations/{gen_id}/tileset/{name}/{filename}")
async def serve_tileset_file(gen_id: int, name: str, filename: str, request: Request):
    """Serve a tileset file."""
    storage_path = Path(request.app.state.storage_path).resolve()
    path = (storage_path / "output" / "tilesets" / name / filename).resolve()

    if not path.is_file():
        raise HTTPException(404)
    if not path.is_relative_to(storage_path):
        raise HTTPException(400, "Invalid path")

    return FileResponse(path, media_type="image/png")


@router.get("/tileset/{name}")
async def get_tileset(name: str, request: Request):
    """List all files in a tileset."""
    storage_path = Path(request.app.state.storage_path)
    tileset_dir = storage_path / "output" / "tilesets" / name
    if not tileset_dir.exists():
        raise HTTPException(404, "Tileset not found")
    files = sorted([f.name for f in tileset_dir.glob("*.png")])
    return {"name": name, "files": files}


class PixelUpdate(BaseModel):
    x: int
    y: int
    color: int


class UpdatePixelsRequest(BaseModel):
    updates: List[PixelUpdate]


@router.post("/generations/{gen_id}/update_pixels")
async def update_pixels(gen_id: int, req: UpdatePixelsRequest, request: Request):
    """Manually update specific pixels in a generation."""
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.get_generation(gen_id)
    if not gen or not gen.pixel_data:
        raise HTTPException(404, "Generation not found or has no pixel data")

    pixel_data = [row[:] for row in gen.pixel_data]

    for update in req.updates:
        x, y, color = update.x, update.y, update.color
        if 0 <= y < gen.size and 0 <= x < gen.size:
            if -1 <= color < len(gen.colors):
                pixel_data[y][x] = color

    db.update_generation_pixels(gen_id, pixel_data, gen.iterations)

    img = pixels_to_image(pixel_data, gen.colors)
    output_dir = storage_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_id = f"gen_{gen_id}_{gen.size}x{gen.size}.png"
    img.save(output_dir / image_id)

    db.update_generation_image(gen_id, str(output_dir / image_id))

    return {"ok": True, "pixel_data": pixel_data}


@router.post("/generations/{gen_id}/finalize")
async def finalize_generation(gen_id: int, request: Request):
    """Finalize a generation (skip remaining iterations)."""
    db = request.app.state.db

    gen = db.get_generation(gen_id)
    if not gen or not gen.pixel_data:
        raise HTTPException(404, "Generation not found or has no pixel data")

    db.update_generation_status(gen_id, GenerationStatus.COMPLETE)
    _notify_gen_update(gen_id)
    db.add_log(gen_id, "finalized", "Manually finalized - skipped remaining iterations")

    return db.get_generation(gen_id)


@router.delete("/generations/{gen_id}")
async def delete_generation(gen_id: int, request: Request):
    """Delete a generation and its associated files."""
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")

    if gen.image_path:
        img_path = Path(gen.image_path)
        if img_path.exists():
            img_path.unlink()

    if gen.reference_path:
        ref_path = Path(gen.reference_path)
        if ref_path.exists():
            ref_path.unlink()

    with db._get_connection() as conn:
        conn.execute("DELETE FROM generation_logs WHERE generation_id = ?", (gen_id,))
        conn.execute("DELETE FROM generations WHERE id = ?", (gen_id,))
        conn.commit()

    return {"ok": True}
