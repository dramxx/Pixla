from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import logging

from app.config import get_settings
from app.db import Database
from app.routes import palettes, generations, models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Pixla API",
    description="Pixel art generator with self-hosted AI models",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "references").mkdir(exist_ok=True)
    (storage_path / "output").mkdir(exist_ok=True)

    app.state.db = Database(settings.db_path)
    app.state.storage_path = settings.storage_path
    logger.info(f"Pixla started - storage: {settings.storage_path}")


@app.on_event("shutdown")
async def shutdown():
    from app.services.diffusion import unload_diffusion
    from app.services.agent import cleanup_agent

    unload_diffusion()
    cleanup_agent()
    logger.info("Pixla shutdown - resources cleaned up")


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/health")
async def health(request: Request):
    status = {"status": "ok", "checks": {}}

    db = getattr(request.app.state, "db", None)
    if db:
        try:
            with db._get_connection() as conn:
                conn.execute("SELECT 1")
            status["checks"]["database"] = "ok"
        except Exception as e:
            status["checks"]["database"] = f"error: {str(e)}"
            status["status"] = "degraded"

    storage_path = Path(settings.storage_path)
    try:
        test_file = storage_path / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        status["checks"]["storage"] = "ok"
    except Exception as e:
        status["checks"]["storage"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status


app.include_router(palettes.router, prefix="/api", tags=["palettes"])
app.include_router(generations.router, prefix="/api", tags=["generations"])
app.include_router(models.router, prefix="/api", tags=["models"])

static_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
    logger.info(f"Serving frontend from: {static_path}")
else:
    logger.warning(f"Frontend build not found at: {static_path}")
