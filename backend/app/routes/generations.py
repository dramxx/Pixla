from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, field_validator
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

    try:
        db.update_generation_status(gen.id, GenerationStatus.GENERATING)
        _notify_gen_update(gen.id)

        references_dir = storage_path / "references"
        references_dir.mkdir(parents=True, exist_ok=True)

        reference_id = f"ref_{gen.id}_{uuid.uuid4().hex[:8]}.png"
        reference_path = references_dir / reference_id

        from app.services.diffusion import get_diffusion, unload_diffusion

        diffusion = get_diffusion(req.model)
        reference = diffusion.generate_pixel_art_reference(
            prompt=req.prompt,
            sprite_type=req.sprite_type.value,
            size=512,
            loras=req.loras,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
        )
        reference.save(reference_path)
        db.update_generation_reference(gen.id, str(reference_path))

        # Free GPU memory after generation
        unload_diffusion()

        if req.reference_only:
            db.update_generation_status(gen.id, GenerationStatus.COMPLETE)
            _notify_gen_update(gen.id)
            gen = db.get_generation(gen.id)
            gen.reference_path = str(reference_path)
            return gen

        if req.use_agent:
            try:
                agent = get_agent()

                import base64
                import io

                ref_bytes = io.BytesIO()
                reference.save(ref_bytes, format="PNG")
                ref_bytes.seek(0)
                ref_b64 = base64.b64encode(ref_bytes.read()).decode()

                system_prompt = f"""A reference concept image is provided. Match its shapes, colors, and composition as closely as possible in pixel art form.

Reference image (base64 PNG): data:image/png;base64,{ref_b64}

{req.system_prompt or ""}"""

                def on_step(iteration: int, step_type: str, message: str):
                    pass

                canvas = agent.run(
                    prompt=req.prompt,
                    palette=req.colors,
                    size=req.size,
                    sprite_type=req.sprite_type.value,
                    max_iterations=40,
                    on_step=on_step,
                )

                pixel_data = canvas.pixels
                # Detect and mark background as transparent
                pixel_data = detect_background(pixel_data)
                iterations = 40

            except Exception as e:
                db.add_log(
                    gen.id, "error", f"Agent failed: {str(e)}. Falling back to quantization."
                )
                print(f"Agent failed, falling back to quantization: {e}")
                pixel_data = quantize_image_to_palette(reference, req.colors, req.size, dither=True)
                pixel_data = detect_background(pixel_data)
                iterations = 1
        else:
            pixel_data = quantize_image_to_palette(reference, req.colors, req.size, dither=True)
            pixel_data = detect_background(pixel_data)
            iterations = 1

        db.update_generation_pixels(gen.id, pixel_data, iterations)

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

    except Exception as e:
        db.update_generation_status(gen.id, GenerationStatus.ERROR, str(e))
        _notify_gen_update(gen.id)
        raise HTTPException(500, str(e))

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

    async def event_generator():
        for _ in range(120):
            gen = db.get_generation(gen_id)
            if gen:
                yield f"data: {json.dumps({'id': gen.id, 'status': gen.status.value, 'iterations': gen.iterations})}\n\n"

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


@router.post("/generations/{gen_id}/chat")
async def chat_with_generation(gen_id: int, req: ChatRequest, request: Request):
    """Continue an existing generation with edit requests."""
    db = request.app.state.db
    storage_path = Path(request.app.state.storage_path)

    gen = db.get_generation(gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")

    if not gen.pixel_data:
        raise HTTPException(400, "No pixel data to edit")

    session = get_session(gen_id)
    if not session:
        raise HTTPException(400, "No active session. Create a new generation to edit.")

    try:
        db.update_generation_status(gen_id, GenerationStatus.GENERATING)
        _notify_gen_update(gen_id)

        def on_step(iteration: int, step_type: str, message: str):
            db.add_log(gen_id, step_type, message)

        agent = get_agent()
        canvas = agent.continue_session(gen_id, req.message, on_step)

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

        cleanup_session(gen_id)

    except Exception as e:
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
    if gen.sprite_type != "block":
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
