"""Shared constants for sprite types across the application."""

SPRITE_TYPE_HINTS = {
    "block": "This is a BLOCK TILE. Fill EVERY pixel — no transparency (-1). The tile will be placed in a grid. Cover the entire canvas.",
    "icon": "This is an ITEM ICON. Draw the object shape and use -1 for background. Keep compact, recognizable.",
    "entity": "This is a CHARACTER SPRITE. Use -1 for transparent areas around the character.",
    "autotile": "This is an AUTOTILE. Design for seamless tiling with edge variants.",
}

DIFFUSION_TYPE_PROMPTS = {
    "block": "Pixel art tile for a 2D side-scrolling platformer game. SQUARE TILE, fills entire canvas edge to edge, seamless, side view, pixel art style.",
    "icon": "Pixel art item icon for a 2D game. Single object centered on transparent background, chunky bold style, clear silhouette.",
    "entity": "Pixel art character sprite for 2D game. Side view, walking pose, clear silhouette, game-ready.",
    "autotile": "Pixel art autotile for 2D game. Multiple states, seamless edges, game tile.",
}

NEGATIVE_PROMPT = (
    "blurry, low quality, photograph, realistic, 3d render, watermark, text, signature"
)
