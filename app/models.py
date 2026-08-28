"""API request, response, and error schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt for image generation")
    count: int = Field(default=4, ge=1, le=4, description="Number of images to generate (1 to 4)")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio (e.g. 16:9, 1:1, 9:16, 4:3, 3:4, 21:9)")
    reference_image_base64: Optional[str] = Field(default=None, description="Optional base64 encoded reference image to upload/guide generation")
    reference_image_url: Optional[str] = Field(default=None, description="Optional URL of a reference image to download and guide generation")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt must not be empty.")
        return v

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        v = v.strip()
        allowed = ["16:9", "1:1", "9:16", "4:3", "3:4", "21:9"]
        if v not in allowed:
            return "16:9"
        return v



class GenerateResponse(BaseModel):
    success: bool = True
    generation_id: str
    model: str
    count: int
    aspect_ratio: str
    images: List[str]
    zip_url: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    details: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str = "ok"


class StatusResponse(BaseModel):
    browser_running: bool
    flow_authenticated: bool
    user_email: Optional[str] = None
    model: str
    busy: bool
    current_generation_id: Optional[str] = None

