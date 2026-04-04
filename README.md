# Pixla

A pixel art generator that paints pixel by pixel using AI.

---

## How It Works (Simple Version)

Regular diffusion model mounts into a fragment of pixel > cleans up the noise in iterations > after several (configured) steps you get image that matches your prompt.

Pixla builds pixel art **pixel by pixel**:

1. You enter a prompt
2. Pixla generates a **reference image** using diffusion model
3. Pixla looks at the sketch and decides: "I need to place a pixel here, and here, and here..."
4. It uses drawing tools: draw lines, fill rectangles, add noise, draw circles
5. Each "move" is intentional — like a human pixel artist working

The agent sees the canvas, thinks about what to draw, places pixels, checks its work, and continues until finished.

---

## Pixla Install Guide

### 1. Backend Setup

```bash
cd pixla/backend
uv sync
```

Create `.env` file:

Start backend:

```bash
cd pixla/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd pixla/frontend
npm install
npm run build # build on localhost:8000
npm run dev # dev server on localhost:3000
```

### 3. Diffusion Model

Place your diffusion models in `backend/storage/models/`:
Consider https://civitai.com/models/195730/aziibpixelmix

Place your Lora's (optional) in `backend/storage/loras/`:
Consider https://civitai.com/models/165876/2d-pixel-toolkit-2d

### 4. LLM Server

Install llama-server and run any LLM
Consider https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/tree/main
