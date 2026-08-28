"""FastAPI application initialization, middleware, and lifecycle management."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from app.config import settings
from app.api.routes import router
from app.services.session_manager import session_manager
from app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FlowBot API Server...")
    settings.profile_path
    settings.output_path
    settings.temp_path
    settings.screenshot_path
    settings.log_path
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

app.include_router(router)
