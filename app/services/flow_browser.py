"""High-level GoogleFlowBrowser orchestrator coordinating sessions and generation."""
from pathlib import Path
from typing import List
from app.services.session_manager import session_manager
from app.services.flow_generator import FlowGeneratorService
from app.services.flow_adapter import FlowAutomationException

class GoogleFlowBrowser:
    @classmethod
    async def generate_images(
        cls,
        prompt: str,
        generation_id: str,
        count: int = 4,
        aspect_ratio: str = "16:9"
    ) -> List[Path]:
        """Main entry point to perform image generation through the browser."""
        page = await session_manager.get_or_create_context()
        generator = FlowGeneratorService(page)
        return await generator.execute_generation(
            prompt=prompt,
            generation_id=generation_id,
            count=count,
            aspect_ratio=aspect_ratio
        )
