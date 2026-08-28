"""API request, response, and error schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt for image generation")
    count: int = Field(default=4, description="Number of images to generate (must be 4)")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio (e.g. 16:9, 1:1, 9:16)")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt must not be empty.")
        return v

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v != 4:
            raise ValueError("ONLY_FOUR_OUTPUTS_SUPPORTED: Exactly 4 outputs required.")
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
    model: str
    busy: bool
    current_generation_id: Optional[str] = None
