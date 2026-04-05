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

# Resolution-specific diffusion prompts for pixel art
RESOLUTION_HINTS = {
    8: "tiny 8x8 pixel art icon, 8-bit style, minimalist, single color masses",
    16: "16x16 pixel art sprite, retro game style, chunky pixels, clear silhouette",
    32: "32x32 pixel art, crisp pixels, no anti-aliasing, game sprite",
    64: "64x64 pixel art, clean edges, sprite format, detailed but limited",
    128: "128x128 pixel art, high detail pixel art, clean lines, game-ready sprite",
}

# Resolution-specific negative prompts
RESOLUTION_NEGATIVE_PROMPTS = {
    8: "smooth gradients, anti-aliasing, blurry, dithering, shading, realistic",
    16: "smooth gradients, anti-aliasing, blurry, excessive dithering, realistic",
    32: "smooth gradients, blurry, photorealistic, realistic shading",
    64: "blurry, photorealistic, smooth gradients",
    128: "blurry, photorealistic",
}
