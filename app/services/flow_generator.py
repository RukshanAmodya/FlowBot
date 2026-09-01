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

    async def wait_for_generation_complete(self, initial_images: set, timeout_seconds: int = 300, expected_count: int = 1) -> List[Locator]:
        """Polls for 0% -> 100% progress and detects when newly generated images are fully rendered."""
        logger.info(f"Generation in progress. Waiting for progress percentage (0% -> 100%) and {expected_count} output(s) to render...")
        start_time = asyncio.get_event_loop().time()

        # Initial wait for generation to spin up
        await self.page.wait_for_timeout(4000)

        # 1. Track ongoing generation progress percentage (e.g. 15%, 50%, 80%, 100%)
        for _ in range(90):
            progress_indicator = self.page.locator("*:has-text('%'), [role='progressbar'], [aria-busy='true']").first
            if await progress_indicator.is_visible(timeout=800):
                try:
                    p_text = await progress_indicator.inner_text()
                    logger.info(f"Generation progress: {p_text}")
                except Exception:
                    pass
                await asyncio.sleep(2)
            else:
                break

        # 2. Wait for newly rendered image elements to appear on the workspace canvas
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

            if len(new_elements) >= expected_count and not is_busy:
                logger.info(f"100% Complete! Detected {len(new_elements)} newly rendered image(s) in workspace.")
                # Give 2 seconds for high-res blob/CDN URLs to settle
                await self.page.wait_for_timeout(2000)
                return new_elements[:expected_count]

            await asyncio.sleep(3)


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
                try:
                    await self.page.goto(settings.FLOW_URL, wait_until="commit", timeout=45000)
                except Exception as e:
                    logger.info(f"Initial navigation notice ({e}); waiting for domcontentloaded...")
                
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=20000)
                except Exception:
                    pass
                await self.page.wait_for_timeout(3000)
            else:
                logger.info(f"Reusing existing open Flow page: {self.page.url}")


            if not await self.adapter.check_authenticated():
                raise FlowAutomationException(
                    "GOOGLE_FLOW_AUTHENTICATION_REQUIRED",
                    "The persistent browser session is no longer authenticated. Run scripts/login.py again."
                )

            # Step 1: Open project workspace directly
            await self.adapter.open_project_or_new()

            # Step 2: Directly upload the reference image
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

                # Step 3: Inside opened reference image view, switch Model from Pro to Nano Banana 2 & 1 image
                logger.info("Inside reference image view: Switching Model to Nano Banana 2...")
                await self.adapter.switch_model_and_settings_in_view(model_name="Nano Banana 2", count=count)


            existing_images = await self.get_existing_image_ids()
            logger.info(f"Found {len(existing_images)} baseline images in workspace.")

            # Step 5: Type prompt directly into the open reference image edit view
            await self.adapter.insert_prompt(prompt)
            await self.adapter.click_generate()


            new_image_elements = await self.wait_for_generation_complete(
                initial_images=existing_images,
                timeout_seconds=settings.GENERATION_TIMEOUT_SECONDS,
                expected_count=count
            )

            # Download generated outputs
            downloaded_paths = await self.downloader.download_generated_images(
                self.page,
                new_image_elements,
                generation_id=generation_id
            )

            logger.info(f"Successfully finished flow generation for ID: {generation_id}")
            return downloaded_paths


        except FlowAutomationException as fae:
            await self.capture_diagnostic_snapshot(f"error_{fae.error_code.lower()}")
            raise
        except Exception as e:
            await self.capture_diagnostic_snapshot("unexpected_error")
            logger.exception(f"Unexpected error during flow generation: {e}")
            raise FlowAutomationException("UNKNOWN_FLOW_ERROR", f"An unexpected error occurred: {str(e)}")
