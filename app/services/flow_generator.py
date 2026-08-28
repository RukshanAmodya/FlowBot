"""Flow generator orchestrator: prompt injection, state tracking, and output detection."""
import asyncio
import datetime
from pathlib import Path
from typing import List
from playwright.async_api import Page, Locator
from app.config import settings
from app.utils.logger import logger
from app.services.flow_adapter import GoogleFlowAdapter, FlowAutomationException
from app.services import flow_selectors as sel
from app.services.image_downloader import ImageDownloader

class FlowGeneratorService:
    def __init__(self, page: Page):
        self.page = page
        self.adapter = GoogleFlowAdapter(page)
        self.downloader = ImageDownloader(settings.output_path, timeout_seconds=settings.DOWNLOAD_TIMEOUT_SECONDS)

    async def capture_diagnostic_snapshot(self, prefix: str = "failure") -> Path:
        """Captures screenshot and HTML snapshot for debugging."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_file = settings.screenshot_path / f"{timestamp}_{prefix}.png"
        html_file = settings.screenshot_path / f"{timestamp}_{prefix}.html"

        try:
            await self.page.screenshot(path=str(screenshot_file), full_page=True)
            content = await self.page.content()
            html_file.write_text(content, encoding="utf-8")
            logger.info(f"Saved diagnostic snapshot to {screenshot_file} and {html_file}")
        except Exception as e:
            logger.error(f"Failed to capture diagnostic snapshot: {e}")

        return screenshot_file

    async def get_existing_image_ids(self) -> set:
        """Collects unique identifiers/sources of all existing images in the DOM."""
        existing = set()
        for container_sel in sel.GENERATED_IMAGE_CONTAINERS:
            try:
                elements = await self.page.locator(container_sel).all()
                for el in elements:
                    src = await el.get_attribute("src") or await el.get_attribute("data-id") or ""
                    if src:
                        existing.add(src)
            except Exception:
                continue
        return existing

    async def wait_for_generation_complete(self, initial_images: set, timeout_seconds: int = 300) -> List[Locator]:
        """Polls for completion signals and detects the newly generated 4 image elements."""
        logger.info("Waiting for generation to finish...")
        start_time = asyncio.get_event_loop().time()

        await self.page.wait_for_timeout(3000)

        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            await self.adapter.check_quota_or_rate_limit()
            is_busy = await self.adapter.is_generating()
            
            new_elements: List[Locator] = []
            for container_sel in sel.GENERATED_IMAGE_CONTAINERS:
                try:
                    elements = await self.page.locator(container_sel).all()
                    for el in elements:
                        src = await el.get_attribute("src") or await el.get_attribute("data-id") or ""
                        if src and src not in initial_images:
                            if await el.is_visible():
                                new_elements.append(el)
                except Exception:
                    continue

            if len(new_elements) >= 4 and not is_busy:
                logger.info(f"Detected {len(new_elements)} new image assets and generation finished.")
                return new_elements[:4]

            await asyncio.sleep(2)

        await self.capture_diagnostic_snapshot("timeout")
        raise FlowAutomationException(
            "GENERATION_TIMEOUT",
            f"Generation timed out after {timeout_seconds} seconds."
        )

    async def execute_generation(
        self,
        prompt: str,
        generation_id: str,
        count: int = 4,
        aspect_ratio: str = "16:9",
        reference_image_base64: str = None,
        reference_image_url: str = None
    ) -> List[Path]:
        """Runs the complete automation lifecycle to generate and download images."""
        logger.info(f"Starting generation flow for ID: {generation_id}")

        try:
            if "labs.google/fx/tools/flow" not in self.page.url:
                logger.info(f"Navigating to {settings.FLOW_URL}...")
                await self.page.goto(settings.FLOW_URL, wait_until="domcontentloaded", timeout=45000)
                await self.page.wait_for_timeout(3000)
            else:
                logger.info(f"Reusing existing open Flow page: {self.page.url}")

            if not await self.adapter.check_authenticated():
                raise FlowAutomationException(
                    "GOOGLE_FLOW_AUTHENTICATION_REQUIRED",
                    "The persistent browser session is no longer authenticated. Run scripts/login.py again."
                )

            await self.adapter.open_project_or_new()
            await self.adapter.select_image_mode()
            await self.adapter.select_nano_banana_2()
            await self.adapter.set_aspect_ratio(aspect_ratio)
            await self.adapter.set_output_count(count)

            # Handle optional reference image
            if reference_image_base64 or reference_image_url:
                ref_path = settings.output_path / generation_id / "reference_input.png"
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                
                if reference_image_base64:
                    import base64
                    raw_b64 = reference_image_base64.split(",", 1)[-1] if "," in reference_image_base64 else reference_image_base64
                    ref_path.write_bytes(base64.b64decode(raw_b64))
                    await self.adapter.upload_reference_image(ref_path)
                elif reference_image_url:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(reference_image_url, timeout=15)
                        if resp.status_code == 200:
                            ref_path.write_bytes(resp.content)
                            await self.adapter.upload_reference_image(ref_path)

            existing_images = await self.get_existing_image_ids()
            logger.info(f"Found {len(existing_images)} baseline images in workspace.")

            await self.adapter.insert_prompt(prompt)
            await self.adapter.click_generate()

            new_image_elements = await self.wait_for_generation_complete(
                initial_images=existing_images,
                timeout_seconds=settings.GENERATION_TIMEOUT_SECONDS
            )

            saved_paths = await self.downloader.download_image_elements(
                page=self.page,
                image_locators=new_image_elements,
                generation_id=generation_id
            )

            return saved_paths


        except FlowAutomationException as fae:
            await self.capture_diagnostic_snapshot(f"error_{fae.error_code.lower()}")
            raise
        except Exception as e:
            await self.capture_diagnostic_snapshot("unexpected_error")
            logger.exception(f"Unexpected error during flow generation: {e}")
            raise FlowAutomationException("UNKNOWN_FLOW_ERROR", f"An unexpected error occurred: {str(e)}")
