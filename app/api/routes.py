"""API routes for FlowBot."""
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Security, Header, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.models import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    StatusResponse,
    ErrorResponse
)
from app.services.session_manager import session_manager
from app.services.flow_browser import GoogleFlowBrowser
from app.services.flow_adapter import FlowAutomationException
from app.utils.logger import logger
from app.utils.files import create_zip_archive

router = APIRouter()
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verifies Bearer API Key if configured."""
    if settings.API_KEY:
        if not credentials or credentials.credentials != settings.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "error": "UNAUTHORIZED", "message": "Invalid or missing API key."}
            )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Healthcheck endpoint."""
    return HealthResponse(status="ok")

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Status endpoint reporting browser and auth state."""
    is_running = await session_manager.is_running()
    is_auth = await session_manager.check_authenticated() if is_running else False
    is_locked = session_manager.lock.locked()
    
    return StatusResponse(
        browser_running=is_running,
        flow_authenticated=is_auth,
        model="Nano Banana 2",
        busy=is_locked,
        current_generation_id=session_manager.current_generation_id
    )

@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    dependencies=[Depends(verify_api_key)]
)
async def generate_images(request: GenerateRequest):
    """Generates 4 images via Google Flow using Nano Banana 2."""
    if session_manager.lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": "GENERATION_IN_PROGRESS",
                "message": "Another image generation job is currently running in the browser session."
            }
        )

    async with session_manager.lock:
        generation_id = uuid.uuid4().hex[:12]
        session_manager.current_generation_id = generation_id
        logger.info(f"Accepted generate request [{generation_id}]: count={request.count}, aspect_ratio={request.aspect_ratio}")
        
        try:
            downloaded_files = await GoogleFlowBrowser.generate_images(
                prompt=request.prompt,
                generation_id=generation_id,
                count=request.count,
                aspect_ratio=request.aspect_ratio,
                reference_image_base64=request.reference_image_base64,
                reference_image_url=request.reference_image_url
            )


            image_urls = [
                f"/generated/{generation_id}/{f.name}"
                for f in downloaded_files
            ]
            zip_url = f"/generation/{generation_id}/download.zip"

            return GenerateResponse(
                success=True,
                generation_id=generation_id,
                model="Nano Banana 2",
                count=len(image_urls),
                aspect_ratio=request.aspect_ratio,
                images=image_urls,
                zip_url=zip_url
            )

        except FlowAutomationException as fae:
            status_code = status.HTTP_400_BAD_REQUEST
            if fae.error_code in ["GENERATION_TIMEOUT", "UNKNOWN_FLOW_ERROR", "IMAGE_DOWNLOAD_FAILED"]:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            elif fae.error_code in ["FLOW_RATE_LIMITED", "QUOTA_EXCEEDED"]:
                status_code = status.HTTP_429_TOO_MANY_REQUESTS

            raise HTTPException(
                status_code=status_code,
                detail={
                    "success": False,
                    "error": fae.error_code,
                    "message": fae.message,
                    "details": fae.details
                }
            )
        except Exception as e:
            logger.exception(f"Unexpected error processing generation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": "UNKNOWN_FLOW_ERROR",
                    "message": f"Server encountered an unexpected error: {str(e)}"
                }
            )
        finally:
            session_manager.current_generation_id = None

@router.get("/generated/{generation_id}/{filename}")
async def get_generated_file(generation_id: str, filename: str):
    """Serves individual generated image files."""
    file_path = (settings.output_path / generation_id / filename).resolve()
    
    if not str(file_path).startswith(str(settings.output_path.resolve())) or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=filename
    )

@router.get("/generation/{generation_id}/download.zip")
async def download_generation_zip(generation_id: str):
    """Packages all 4 generated images into a single zip archive for download."""
    gen_dir = settings.output_path / generation_id
    if not gen_dir.exists() or not gen_dir.is_dir():
        raise HTTPException(status_code=404, detail="Generation not found")
    
    image_files = sorted(list(gen_dir.glob("image_*.png")))
    if not image_files:
        raise HTTPException(status_code=404, detail="No images found for this generation")
    
    zip_path = gen_dir / f"generation_{generation_id}.zip"
    if not zip_path.exists():
        create_zip_archive(image_files, zip_path)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"generation_{generation_id}.zip"
    )

@router.post("/auth/upload-session")
async def upload_browser_session(request: Request):
    """Uploads and applies browser_profile.zip directly to VPS server."""
    import shutil
    import zipfile

    form = await request.form()
    file_item = form.get("file")
    if not file_item:
        raise HTTPException(status_code=400, detail="No session zip file provided")

    zip_tmp = settings.temp_path / "browser_profile_uploaded.zip"
    with open(zip_tmp, "wb") as f:
        f.write(await file_item.read())

    # Close active browser session before overwriting profile
    await session_manager.close()

    # Extract into browser_profile
    with zipfile.ZipFile(zip_tmp, "r") as zip_ref:
        zip_ref.extractall(settings.profile_path)

    if zip_tmp.exists():
        zip_tmp.unlink()

    logger.info("Successfully received and extracted browser_profile onto VPS!")
    return {
        "success": True,
        "message": "Browser profile and Google login session successfully applied to VPS!"
    }

