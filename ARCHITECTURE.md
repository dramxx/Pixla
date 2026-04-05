# Architecture Guide for Pixla

## Overview

This document explains the architecture of Pixla — how the components work together to generate pixel art using self-hosted AI models.

---

## High-Level Architecture

User Request → POST /api/generations
│
├─► 1. Diffusion (512px reference) → downscale to target
│
├─► 2. LLM Agent draws on canvas
│ - Starts with BLANK canvas
│ - Reference shown as base64 image
│ - Calls tools: fill_rect, draw_pixel, etc.
│ - 40 iterations max
│
└─► 3. Fallback to quantization if agent fails

```
┌─────────────────────────────────────────────────────────────────┐
│                          User (Browser)                         │
│                              │                                  │
│                    HTTPS/WSS (HTTP API)                         │
│                              │                                  │
└──────────────────────────────▼──────────────────────────────────┘
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
         ┌──────────────────┐            ┌──────────────┐  ┌────────┐
         │   Model Manager  │            │   Database   │  │Storage │
         │ - Load models    │            │   (SQLite)   │  │        │
         │ - Apply LoRAs    │            │              │  │        │
         └─────────┬────────┘            └──────────────┘  └────────┘
                   │
                   ▼
         ┌────────────────────────┐
         │   Diffusion Service    │
         │  - Generate images     │
         │  - Apply LoRAs         │
         └────────────────────────┘
                   │
                   ▼
         ┌────────────────────────┐
         │   LLM Agent            │
         │  - Draw pixels         │
         │  - Use canvas tools    │
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
- `Home.tsx` — Main generation page with canvas and controls
- `Canvas.tsx` — Pixel art display
- `ControlPanel.tsx` — Generation controls (prompt, model, LoRA, palette)
- `History.tsx` — List of past generations

**State Management**:

- Zustand stores for UI state
- API client for backend communication
- SSE (Server-Sent Events) for real-time updates

**API Communication**:

```typescript
GET  /api/palettes                // List palettes
POST /api/generations             // Create generation
GET  /api/generations/:id          // Get result
GET  /api/generations/:id/stream   // SSE progress
GET  /api/generations/:id/download  // Download PNG
POST /api/generations/:id/edit    // Edit existing generation
GET  /api/models                  // List available models
GET  /api/loras                   // List available LoRAs
```

### Backend (Python + FastAPI)

**Purpose**: API server, AI inference orchestration, data management

**Structure**:

```
backend/
├── app/
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Settings
│   ├── routes/
│   │   ├── palettes.py           # Palette endpoints
│   │   ├── generations.py        # Generation endpoints
│   │   └── models.py             # Model/LoRA discovery
│   ├── services/
│   │   ├── diffusion.py         # Stable Diffusion inference
│   │   ├── quantization.py      # Palette quantization
│   │   ├── agent.py              # LLM agent for pixel drawing
│   │   ├── autotile.py           # Autotile/tileset generation
│   │   └── canvas.py              # Canvas manipulation
│   └── db/
│       └── sqlite.py             # Database operations
```

### Diffusion Service

**Purpose**: Generate reference images from text prompts using local models

**Workflow**:

1. Receive prompt + sprite type
2. Build enhanced prompt with sprite-type and resolution hints
3. Load model (if not cached)
4. Generate 512x512 image
5. Downscale to target size using Lanczos

### LLM Agent

**Purpose**: Use LLM to draw pixel art using canvas tools

**Workflow**:

```
1. Start with empty canvas
2. Send reference image (base64) + prompt + palette + tools to LLM
3. LLM calls tools: draw_pixel, fill_rect, draw_line, noise_fill, etc.
4. Repeat up to 40 iterations
5. On failure: fall back to quantization
```

**Available Tools**:

- `draw_pixel(x, y, color)` — Set single pixel
- `fill_rect(x1, y1, x2, y2, color)` — Fill rectangle
- `fill_row/fill_column` — Fill lines
- `draw_line` — Draw lines
- `draw_circle/draw_ellipse` — Draw shapes
- `noise_fill_rect/noise_fill_circle` — Add texture
- `voronoi_fill` — Voronoi pattern fill
- `view_canvas` — See current state
- `finish` — Complete generation

### Palette Quantization

**Purpose**: Convert full-color diffusion output to limited palette pixel art

**Algorithms**:

- **Nearest neighbor**: Simple color mapping
- **Floyd-Steinberg dithering**: Quality dithering with error diffusion

**Process**:

```
Diffusion Output → Resize to target → Quantize to palette → Background detection → PNG
```

### Autotile Generation

**Purpose**: Generate 16 tile variants from a base tile for seamless tiling

**Bitmask**: TOP=1, RIGHT=2, BOTTOM=4, LEFT=8

### Database (SQLite)

**Schema**:

```sql
CREATE TABLE palettes (
    id INTEGER PRIMARY KEY,
    name TEXT,
    colors TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE generations (
    id INTEGER PRIMARY KEY,
    prompt TEXT,
    colors TEXT,
    size INTEGER,
    sprite_type TEXT,
    pixel_data TEXT,
    iterations INTEGER,
    status TEXT,
    image_path TEXT,
    reference_path TEXT,
    error_message TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE generation_logs (
    id INTEGER PRIMARY KEY,
    generation_id INTEGER,
    step TEXT,
    message TEXT,
    created_at TEXT
);
```

---

## Data Flow

### Generation Flow

```
1. User submits generation request
   │
   ▼
2. Backend creates generation record (status: generating)
   │
   ▼
3. Diffusion generates 512x512 reference image
   │
   ▼
4. Downscale to target size (LANCZOS)
   │
   ▼
5. LLM Agent draws on canvas using tools
   │    (40 iterations max, reference shown as image)
   │    On failure: fall back to quantization
   ▼
6. Detect background transparency
   │
   ▼
7. Save PNG to storage/output/
   │
   ▼
8. Frontend receives SSE update → display result
```

### Edit Flow

```
1. User checks "Edit" checkbox on existing generation
   │
   ▼
2. User enters edit request (e.g., "add more detail to handle")
   │
   ▼
3. Backend loads existing pixel data as canvas
   │
   ▼
4. LLM Agent modifies existing canvas
   │
   ▼
5. Save updated PNG
```

---

## API Design

### REST Endpoints

```
Palettes
GET    /api/palettes              → list[Palette]
POST   /api/palettes              → Palette
GET    /api/palettes/{id}          → Palette
PUT    /api/palettes/{id}          → Palette
DELETE /api/palettes/{id}         → {ok: bool}

Generations
POST   /api/generations           → Generation
GET    /api/generations            → list[Generation]
GET    /api/generations/{id}       → Generation
GET    /api/generations/{id}/stream  → SSE stream
GET    /api/generations/{id}/download → PNG file
POST   /api/generations/{id}/edit  → Generation
POST   /api/generations/{id}/tileset → Tileset variants

Models
GET    /api/models                 → list[ModelConfig]
GET    /api/models/{id}             → ModelConfig

LoRAs
GET    /api/loras                   → list[LoRAConfig]
GET    /api/loras/{id}              → LoRAConfig
```

---

## Configuration

### Environment Variables

```bash
# Server
HOST=localhost
PORT=8000
DEBUG=false

# Database
DB_PATH=./pixla.db

# Storage
STORAGE_PATH=./storage

# Diffusion Model
MODEL_DEVICE=cuda
MODEL_DTYPE=float16

# LLM (for pixel drawing agent)
LLM_HOST=localhost
LLM_PORT=8081
LLM_MODEL=qwen2.5-7b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
```

---

## Deployment

### Development

```bash
# Backend
cd backend
uv sync
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Related Documents

- [README.md](./README.md) — Quick start and setup
