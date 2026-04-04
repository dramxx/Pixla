# Architecture Guide for Pixla

## Overview

This document explains the architecture of Pixla — how the components work together to generate pixel art using self-hosted AI models.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User (Browser)                         │
│                              │                                  │
│                    HTTPS/WSS (HTTP API)                         │
│                              │                                  │
└───────────────────────────────▼─────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
           ┌─────────────────┐               ┌─────────────────┐
           │   Frontend      │               │   Backend       │
           │  (Vite+React)   │◄──────────────│  (FastAPI)      │
           └─────────────────┘               └────────┬────────┘
                                                      │
                    ┌─────────────────────────────────┼─────────┐
                    │                                 │         │
                    ▼                                 ▼         ▼
        ┌───────────────────┐            ┌──────────────┐  ┌────────┐
        │   Model Manager   │            │   Database   │  │Storage │
        │ - Load models     │            │   (SQLite)   │  │        │
        │ - Apply LoRAs     │            │              │  │        │
        └─────────┬─────────┘            └──────────────┘  └────────┘
                  │
                  ▼
        ┌────────────────────────┐
        │   Diffusion Service    │
        │  - Generate images     │
        │  - Apply LoRAs         │
        │  - Quantize palette    │
        └────────────────────────┘
                  │
                  ▼
        ┌────────────────────────┐
        │   LLM Agent            │
        │  - Refine pixels       │
        │  - Add details         │
        └────────────────────────┘
                  │
                  ▼
        ┌────────────────────────┐
        │    Output Image        │
        │    (PNG file)          │
        └────────────────────────┘
```

---

## Components

### Frontend (Vite + React + TypeScript)

**Purpose**: User interface for configuring and running generations

**Key Components**:

- `App.tsx` — Main routing and layout
- `Layout.tsx` — Navigation bar and overall layout structure
- `Home.tsx` — Main generation page with three-column layout
- `Canvas.tsx` — Pixel art display and editing
- `ControlPanel.tsx` — All generation controls (prompt, model, LoRA, sampling, palette)

**State Management**:

- Zustand stores for UI state
- API client for backend communication
- SSE (Server-Sent Events) for real-time updates

**API Communication**:

```typescript
// Frontend → Backend examples
GET  /api/palettes           // List palettes
POST /api/generations        // Create generation
GET  /api/generations/:id    // Get result
GET  /api/generations/:id/stream  // SSE progress
GET  /api/models            // List available models
POST /api/models            // Upload new model
```

### Backend (Python + FastAPI)

**Purpose**: API server, AI inference orchestration, data management

**Structure**:

```
backend/
├── app/
│   ├── main.py             # FastAPI app entry
│   ├── config.py           # Settings
│   ├── routes/
│   │   ├── palettes.py     # Palette endpoints
│   │   ├── generations.py  # Generation endpoints
│   │   ├── models.py       # Model management
│   │   └── files.py        # Static file serving
│   ├── services/
│   │   ├── diffusion.py    # Stable Diffusion inference
│   │   ├── quantization.py # Palette quantization
│   │   ├── agent.py        # LLM agent for pixel refinement
│   │   ├── autotile.py     # Autotile/tileset generation
│   │   └── canvas.py        # Canvas manipulation
│   ├── models/
│   │   ├── config.py       # Model/LoRA configs
│   │   ├── palette.py      # Palette model
│   │   └── generation.py  # Generation model
│   └── db/
│       └── sqlite.py       # Database operations
```

### Model Discovery

**Purpose**: Discover models and LoRAs from storage folders

**How it works**:

- User downloads models/LoRAs to `storage/models/` and `storage/loras/`
- App scans folders and reads `config.json` if present
- Returns list of available models for frontend selection

**Folder Structure**:

```
storage/
├── models/                    # User-downloaded diffusion models
│   ├── stable-diffusion-v1-5/
│   │   └── config.json        # Optional model config
│   └── pixel-art-sd/
├── loras/                     # User-downloaded LoRAs
│   ├── pixel-art-style/
│   └── game-assets/
```

**Note**: Currently no upload functionality - user manages files directly in folders. This keeps the app simple while allowing full control over models.

### Diffusion Service

**Purpose**: Generate images from text prompts using local models

**Workflow**:

1. Receive prompt + config
2. Build enhanced prompt (sprite-type specific)
3. Load model (if not cached)
4. Generate image with diffusion
5. Return PIL Image

**Key Code**:

```python
def generate(self, prompt: str, config: GenerationConfig) -> Image:
    # Sprite-type prompt enhancement
    enhanced = enhance_prompt(prompt, config.sprite_type)

    # Run diffusion
    result = self.pipeline(
        prompt=enhanced,
        negative_prompt="blurry, low quality...",
        num_inference_steps=config.steps,
        guidance_scale=config.guidance_scale,
    )

    return result.images[0]
```

### Palette Quantization

**Purpose**: Convert full-color diffusion output to limited palette pixel art

**Algorithms**:

- **Nearest neighbor**: Simple, fast, lower quality
- **Floyd-Steinberg dithering**: Better quality, artistic
- **Ordered dithering**: Faster than Floyd-Steinberg

**Process**:

```
Diffusion Output (RGBA)  →  Resize to target (e.g., 16x16)
                                    ↓
                         For each pixel: find closest palette color
                                    ↓
                         2D array of palette indices
                                    ↓
                         Convert to PNG with palette colors
```

### Agent (LLM Refinement)

**Purpose**: Use LLM to refine and add details to quantized pixels

**Status**: ✅ **IMPLEMENTED**

**Why Optional**:

- Diffusion → Quantization often produces good results
- Agent adds latency (LLM calls)
- For simple sprites, skip agent

**Workflow**:

```
Initial Pixels + Prompt + Palette + Tools
        ↓
    LLM Loop (ReAct style)
        ↓
    - view_canvas: See current state
    - draw_pixel, fill_rect, etc.: Modify
        ↓
    Final refined pixels
```

### Autotile Generation

**Purpose**: Generate 16 tile variants from a base tile for seamless tiling

**Status**: ✅ **IMPLEMENTED**

**How it works**:

- Takes base pixel art tile (e.g., grass block)
- Generates 16 variants using bitmask (TOP=1, RIGHT=2, BOTTOM=4, LEFT=8)
- Applies edge shading, outlines, and rounded corners based on adjacent tiles
- Creates seamless tilesets for game maps

**Bitmask Examples**:

- `0` = isolated (all edges exposed)
- `15` = surrounded (no edges exposed)
- `1` = top edge only, `2` = right edge only, etc.

**Process**:

```python
# Generate all 16 variants
tileset = generate_tileset(pixel_data, palette, size)
# Returns: {0: Image, 1: Image, ..., 15: Image}
```

### Database (SQLite)

**Purpose**: Store palettes, generations, configs

**Schema**:

```sql
CREATE TABLE palettes (
    id INTEGER PRIMARY KEY,
    name TEXT,
    colors TEXT,  -- JSON array
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE generations (
    id INTEGER PRIMARY KEY,
    prompt TEXT,
    colors TEXT,
    size INTEGER,
    sprite_type TEXT,
    pixel_data TEXT,  -- JSON 2D array
    status TEXT,
    image_path TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

### Storage

**Purpose**: File storage for models, LoRAs, generated images

```
storage/
├── models/              # AI models
│   ├── stable-diffusion-v1-5/
│   └── pixel-art-sd/
├── loras/               # LoRA adapters
│   ├── pixel-art-style/
│   └── game-assets/
├── references/          # Generated reference images
└── output/             # Final pixel art PNGs
```

---

## Data Flow

### Generation Flow (Full)

```
1. User submits generation request
   │
   ▼
2. Backend creates generation record (status: pending)
   │
   ▼
3. Diffusion service generates reference image
   │
   ▼
4. Quantization converts to palette indices
   │
   ▼
5. (Optional) Agent refines pixels
   │
   ▼
6. Save PNG to storage
   │
   ▼
7. Update generation record (status: complete)
   │
   ▼
8. Frontend polls/gets SSE update
   │
   ▼
9. User sees result, downloads PNG
```

### Real-Time Updates (SSE)

```python
# Backend: generations.py - Event-driven SSE using asyncio.Event
gen_events = {}  # Global dict for generation events

def _get_gen_event(gen_id: int) -> asyncio.Event:
    if gen_id not in gen_events:
        gen_events[gen_id] = asyncio.Event()
    return gen_events[gen_id]

def _notify_gen_update(gen_id: int):
    if gen_id in gen_events:
        gen_events[gen_id].set()

@router.get("/generations/{id}/stream")
async def stream_generation(id: int, request: Request):
    event = _get_gen_event(id)

    async def event_generator():
        for _ in range(120):  # 2 minute timeout
            gen = db.get_generation(id)
            if gen:
                yield f"data: {json.dumps({'id': gen.id, 'status': gen.status.value, 'iterations': gen.iterations})}\n\n"

            if gen and gen.status in ["complete", "error"]:
                _clear_gen_event(id)
                break

            await event.wait(timeout=1.0)  # Event-driven, not polling
            event.clear()

        _clear_gen_event(id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## API Design

### REST Endpoints

```
Palettes
GET    /api/palettes              → list[Palette]
POST   /api/palettes              → Palette
GET    /api/palettes/{id}         → Palette
PUT    /api/palettes/{id}         → Palette
DELETE /api/palettes/{id}         → {success: bool}

Generations
POST   /api/generations          → Generation (starts async)
GET    /api/generations          → list[Generation]
GET    /api/generations/{id}     → Generation
GET    /api/generations/{id}/stream → SSE stream
GET    /api/generations/{id}/download → PNG file

Models
GET    /api/models               → list[ModelConfig] (discover from folder)
GET    /api/models/{id}           → ModelConfig
GET    /api/models/default       → ModelConfig (default model)

LoRAs
GET    /api/loras                 → list[LoRAConfig] (discover from folder)
GET    /api/loras/{id}            → LoRAConfig
```

### Request/Response Examples

```json
// POST /api/generations
{
  "prompt": "a medieval iron sword",
  "colors": ["#000000", "#FFFFFF", "#8B4513", "#C0C0C0"],
  "size": 16,
  "sprite_type": "icon",
  "model_id": "pixel-art-sd",
  "loras": [
    {"id": "game-assets", "scale": 0.8, "enabled": true}
  ]
}

// Response
{
  "id": 1,
  "status": "generating",
  "prompt": "a medieval iron sword",
  "pixel_data": null,
  "created_at": "2025-04-03T12:00:00Z"
}

// SSE update
{"id": 1, "status": "generating", "iterations": 5}

// Final
{"id": 1, "status": "complete", "pixel_data": [[0,1,1,0],[...]], "image_path": "gen_1_16x16.png"}
```

---

## Configuration

### Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database
DB_PATH=./pixla.db

# Storage
STORAGE_PATH=./storage

# AI Models (default)
MODEL_ID=runwayml/stable-diffusion-v1-5
MODEL_DEVICE=cuda  # or "cpu"
MODEL_DTYPE=float16  # or "float32"

# Optional: API fallback
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Hardware Requirements

| Setup       | GPU           | RAM  | Storage | Speed  |
| ----------- | ------------- | ---- | ------- | ------ |
| Minimum     | GTX 1060 6GB  | 16GB | 10GB    | 30-60s |
| Recommended | RTX 3070 8GB  | 32GB | 50GB    | 10-30s |
| Production  | RTX 4090 24GB | 64GB | 100GB   | 5-15s  |

---

## Security Considerations

- **No authentication** (single-user local deployment)
- **API key protection** (optional, for API endpoints)
- **File upload validation** (check file types, sizes)
- **Path traversal prevention** (sanitize paths)

---

## Deployment

### Development

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Production (Docker)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/ .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
    environment:
      - MODEL_DEVICE=cuda # if GPU available
```

---

## Monitoring & Debugging

### Logging

- FastAPI logs → stdout
- Generation logs → database (generation_logs table)
- Model loading → console output

### Health Checks

```
GET /health → {status: "ok"}
```

### Metrics to Track

- Generation time
- Model load time
- Memory usage (VRAM)
- Generation success rate

---

## Future Enhancements

### v1.1 (Current)

- [ ] **Progress status** - Better generation progress indicators
- [ ] **Download fixes** - Fix PNG download functionality
- [ ] **Edit mode** - Fix hidden edit mode in history page
- [ ] **Canvas sizing** - Make generated images fit container properly
- [ ] **Performance benchmarking** - Add performance metrics
- [ ] **Security testing** - Add security test suite

### v1.2 (Planned)

- [ ] **Diffusion-only mode** - Option to return only diffusion image without quantization

### v1.3 (Planned)

- [ ] **Manual Canvas Editing** - Click-to-draw pixel art editor

### Future Versions

- [ ] **CivitAI integration** — Download models directly
- [ ] **ControlNet** — Image-to-image with control
- [ ] **Training UI** — Fine-tune LoRAs
- [ ] **Batch generation** — Generate multiple variants
- [ ] **Sprite sheets** — Multi-frame output
- [ ] **WebSocket** — More efficient real-time than SSE (if agent needs bidirectional chat)
- [ ] **Model management UI** — Web interface for model/LoRA management

---

## Related Documents

- [USER.md](./USER.md) — User guide and walkthrough
- [README.md](./README.md) — Implementation status and quick start
