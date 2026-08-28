"""Downloads and saves generated images to permanent/static storage."""
import asyncio
from pathlib import Path
from typing import List
import httpx
from playwright.async_api import Page, Locator
from app.utils.logger import logger
from app.services.flow_adapter import FlowAutomationException

class ImageDownloader:
    def __init__(self, output_base_dir: Path, timeout_seconds: int = 120):
        self.output_base_dir = output_base_dir
        self.timeout_seconds = timeout_seconds

    async def download_image_elements(
        self,
        page: Page,
        image_locators: List[Locator],
        generation_id: str
    ) -> List[Path]:
        """Downloads the 4 image files directly to the generation directory."""
        gen_dir = self.output_base_dir / generation_id
        gen_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: List[Path] = []

        logger.info(f"Beginning download of {len(image_locators)} image assets for generation {generation_id}...")

        for idx, loc in enumerate(image_locators, 1):
            target_file = gen_dir / f"image_{idx}.png"
            downloaded = False

            try:
                src = await loc.get_attribute("src")
                if src and src.startswith("http"):
                    logger.info(f"Downloading image #{idx} via src URL...")
                    response = await page.request.get(src)
                    if response.ok:
                        body = await response.body()
                        target_file.write_bytes(body)
                        downloaded = True

                if not downloaded:
                    download_btn = loc.locator("button[aria-label*='Download'], button[title*='Download']").first
                    if await download_btn.is_visible(timeout=1000):
                        async with page.expect_download(timeout=self.timeout_seconds * 1000) as download_info:
                            await download_btn.click()
                        download = await download_info.value
                        await download.save_as(str(target_file))
                        downloaded = True

                if not downloaded and src and src.startswith("data:image"):
                    import base64
                    header, encoded = src.split(",", 1)
                    target_file.write_bytes(base64.b64decode(encoded))
                    downloaded = True

                if downloaded and target_file.exists() and target_file.stat().st_size > 0:
                    logger.info(f"Successfully saved image #{idx} to {target_file}")
                    saved_paths.append(target_file)
                else:
                    logger.error(f"Failed to download valid image asset #{idx}")
            except Exception as e:
                logger.error(f"Error downloading asset #{idx}: {e}")

        if len(saved_paths) != 4:
            raise FlowAutomationException(
                "IMAGE_DOWNLOAD_FAILED",
                f"Expected 4 downloaded image assets, but only successfully downloaded {len(saved_paths)}."
            )

        return saved_paths
