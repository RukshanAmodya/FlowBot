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
                # If locator is a container/tile rather than an <img>, locate child <img>
                img_loc = loc if await loc.evaluate("el => el.tagName.toLowerCase() === 'img'") else loc.locator("img").first
                src = await img_loc.get_attribute("src") if await img_loc.is_visible(timeout=1000) else await loc.get_attribute("src")

                if src:
                    if src.startswith("/"):
                        src = f"https://labs.google{src}"

                    logger.info(f"Downloading image #{idx} from {src[:80]}...")
                    # Strategy 1: Use Playwright browser session request context (shares auth cookies & headers)
                    try:
                        response = await page.request.get(src)
                        if response.ok:
                            body = await response.body()
                            if len(body) > 1000:
                                target_file.write_bytes(body)
                                downloaded = True
                                logger.info(f"Downloaded #{idx} via page.request (size: {len(body)} bytes)")
                    except Exception as req_err:
                        logger.warning(f"page.request.get error on #{idx}: {req_err}")

                    # Strategy 2: In-browser canvas/fetch evaluation
                    if not downloaded:
                        logger.info(f"Attempting in-browser fetch for image #{idx}...")
                        base64_data = await page.evaluate(
                            """async (url) => {
                                try {
                                    const resp = await fetch(url, { credentials: 'include' });
                                    const blob = await resp.blob();
                                    return new Promise((resolve) => {
                                        const reader = new FileReader();
                                        reader.onloadend = () => resolve(reader.result);
                                        reader.readAsDataURL(blob);
                                    });
                                } catch(e) {
                                    return null;
                                }
                            }""",
                            src
                        )
                        if base64_data and "," in base64_data:
                            import base64
                            _, encoded = base64_data.split(",", 1)
                            img_bytes = base64.b64decode(encoded)
                            if len(img_bytes) > 1000:
                                target_file.write_bytes(img_bytes)
                                downloaded = True
                                logger.info(f"Downloaded #{idx} via browser JS fetch (size: {len(img_bytes)} bytes)")

                # Strategy 3: Click UI download button if present
                if not downloaded:
                    download_btn = loc.locator("button[aria-label*='Download'], button[title*='Download']").first
                    if await download_btn.is_visible(timeout=1000):
                        async with page.expect_download(timeout=self.timeout_seconds * 1000) as download_info:
                            await download_btn.click()
                        download = await download_info.value
                        await download.save_as(str(target_file))
                        downloaded = True

                # Strategy 4: Direct base64 inline src
                if not downloaded and src and src.startswith("data:image"):
                    import base64
                    header, encoded = src.split(",", 1)
                    target_file.write_bytes(base64.b64decode(encoded))
                    downloaded = True

                if downloaded and target_file.exists() and target_file.stat().st_size > 0:
                    logger.info(f"Successfully saved image #{idx} to {target_file} (size={target_file.stat().st_size} bytes)")
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
