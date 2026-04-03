from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from typing import List


router = APIRouter()


class CreatePaletteRequest(BaseModel):
    name: str
    colors: List[str]

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


@router.get("/palettes")
async def list_palettes(request: Request):
    db = request.app.state.db
    return db.list_palettes()


@router.post("/palettes")
async def create_palette(req: CreatePaletteRequest, request: Request):
    db = request.app.state.db
    return db.create_palette(req.name, req.colors)


@router.get("/palettes/{palette_id}")
async def get_palette(palette_id: int, request: Request):
    db = request.app.state.db
    palette = db.get_palette(palette_id)
    if not palette:
        raise HTTPException(404, "Palette not found")
    return palette


@router.put("/palettes/{palette_id}")
async def update_palette(palette_id: int, req: CreatePaletteRequest, request: Request):
    db = request.app.state.db
    palette = db.update_palette(palette_id, req.name, req.colors)
    if not palette:
        raise HTTPException(404, "Palette not found")
    return palette


@router.delete("/palettes/{palette_id}")
async def delete_palette(palette_id: int, request: Request):
    db = request.app.state.db
    if not db.delete_palette(palette_id):
        raise HTTPException(404, "Palette not found")
    return {"success": True}
