from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.routes import router
from app.services.session_manager import session_manager
from app.utils.logger import logger

static_dir = Path(__file__).resolve().parent.parent / "static"
static_dir.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FlowBot API Server...")
    settings.profile_path
    settings.output_path
    settings.temp_path
    settings.screenshot_path
    settings.log_path
    settings.output_path.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutting down FlowBot API Server...")
    await session_manager.close()

app = FastAPI(
    title="Google Flow Nano Banana 2 API Bot",
    version="1.0.0",
    description="Local-first HTTP API controlling authenticated Google Flow for Nano Banana 2 image generation.",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg", "Invalid request parameters") if errors else "Validation error"
    error_code = "INVALID_REQUEST"
    if "ONLY_FOUR_OUTPUTS_SUPPORTED" in msg or any("count" in str(e.get("loc", [])) for e in errors):
        error_code = "ONLY_FOUR_OUTPUTS_SUPPORTED"

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": error_code,
            "message": msg,
            "details": jsonable_encoder(errors)
        }
    )

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def serve_root_dashboard():
    """Serves the FlowBot Studio Web UI dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "FlowBot Studio API is running. Visit /docs for documentation."}

app.include_router(router)

