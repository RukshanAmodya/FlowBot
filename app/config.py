"""Configuration module for FlowBot application."""
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Google Flow Settings
    FLOW_URL: str = "https://labs.google/fx/tools/flow/project/3e041cb7-020b-49de-9bbf-6dbf42ac5469"
    FLOW_MODEL: str = "NANO_BANANA_2"

    IMAGE_COUNT: int = 4
    ASPECT_RATIO: str = "16:9"
    OUTPUT_STRATEGY: Literal["single_request", "multiple_requests"] = "single_request"

    # Browser Automation Settings
    BROWSER_PROFILE_DIR: str = "./browser_profile"
    HEADLESS: bool = False
    FLOW_DEBUG: bool = False
    GENERATION_TIMEOUT_SECONDS: int = 300
    DOWNLOAD_TIMEOUT_SECONDS: int = 120

    # API Server Settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_KEY: str = ""

    # Storage Paths
    OUTPUT_DIR: str = "./generated"
    TEMP_DIR: str = "./temp"
    SCREENSHOT_DIR: str = "./screenshots"
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"

    @property
    def profile_path(self) -> Path:
        p = Path(self.BROWSER_PROFILE_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_path(self) -> Path:
        p = Path(self.OUTPUT_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def temp_path(self) -> Path:
        p = Path(self.TEMP_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def screenshot_path(self) -> Path:
        p = Path(self.SCREENSHOT_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_path(self) -> Path:
        p = Path(self.LOG_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
