"""Adapter layer abstracting interaction with Google Flow DOM."""
import asyncio
from pathlib import Path
from typing import List, Optional
from playwright.async_api import Page, Locator
from app.services import flow_selectors as sel
from app.utils.logger import logger

class FlowAutomationException(Exception):
    def __init__(self, error_code: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class GoogleFlowAdapter:
    def __init__(self, page: Page):
        self.page = page

    async def find_element(self, selectors: List[str], timeout_ms: int = 5000) -> Optional[Locator]:
        """Tries a list of fallback selectors until one is visible and usable."""
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if await locator.is_visible(timeout=timeout_ms // len(selectors)):
                    return locator
            except Exception:
                continue
        return None

    async def check_authenticated(self) -> bool:
        """Verifies whether the current page has an active Google Flow session."""
        try:
            for sign_in_sel in sel.SIGN_IN_BUTTON_SELECTORS:
                if await self.page.locator(sign_in_sel).is_visible(timeout=2000):
                    return False
            url = self.page.url
            if "accounts.google.com" in url or "signin" in url:
                return False
            return True
        except Exception as e:
            logger.warning(f"Failed to verify authentication status: {e}")
            return False

    async def open_project_or_new(self) -> None:
        """Ensures an active project/workspace is open, reusing existing active project."""
        logger.info("Checking for active project workspace...")
        # If the prompt editor or workspace canvas is already visible or URL contains /project/, stay in the same project
        if "/project/" in self.page.url:
            logger.info(f"Already in active project workspace: {self.page.url}. Reusing existing project.")
            return

        prompt_box = await self.find_element(sel.PROMPT_INPUT_SELECTORS, timeout_ms=2000)
        if prompt_box and await prompt_box.is_visible():
            logger.info("Prompt input already available in workspace. Reusing existing project.")
            return

        new_proj_btn = await self.find_element(sel.NEW_PROJECT_SELECTORS, timeout_ms=3000)
        if new_proj_btn:
            logger.info("Found 'New Project' button. Initializing project workspace...")
            await new_proj_btn.click()
            await self.page.wait_for_timeout(2000)


    async def select_image_mode(self) -> None:
        """Ensures Image mode is selected."""
        logger.info("Selecting Image mode...")
        img_tab = await self.find_element(sel.IMAGE_MODE_SELECTORS, timeout_ms=3000)
        if img_tab:
            await img_tab.click()
            await self.page.wait_for_timeout(500)
        else:
            logger.info("Image mode button not found or already default.")

    async def select_nano_banana_2(self) -> None:
        """Explicitly selects Nano Banana 2 model or fails if unavailable."""
        logger.info("Attempting to select model: Nano Banana 2...")
        body_text = await self.page.inner_text("body")

        dropdown = await self.find_element(sel.MODEL_DROPDOWN_SELECTORS, timeout_ms=3000)
        if dropdown:
            await dropdown.click()
            await self.page.wait_for_timeout(1000)

        model_option = await self.find_element(sel.NANO_BANANA_2_SELECTORS, timeout_ms=4000)
        if model_option:
            await model_option.click()
            logger.info("Successfully selected Nano Banana 2.")
            await self.page.wait_for_timeout(1000)
        else:
            if "Nano Banana 2" in body_text:
                logger.info("Nano Banana 2 appears already active in the interface.")
            else:
                raise FlowAutomationException(
                    "NANO_BANANA_2_UNAVAILABLE",
                    "Nano Banana 2 could not be selected in the current Google Flow session."
                )

    async def set_aspect_ratio(self, ratio: str = "16:9") -> None:
        """Configures the aspect ratio (e.g., 16:9, 1:1, 9:16, 4:3, 3:4, 21:9)."""
        logger.info(f"Configuring aspect ratio to {ratio}...")
        try:
            # Model & settings trigger button (e.g. [🍌 Nano Banana 2  crop_16_9  x4])
            badge_trigger = self.page.locator("button:has-text('Banana'), button:has-text('Nano'), button:has(i:has-text('crop_'))").first
            if await badge_trigger.is_visible(timeout=1500):
                await badge_trigger.click()
                await self.page.wait_for_timeout(600)

                # Ratio icons or buttons inside popup
                ratio_loc = self.page.locator(f"button:has-text('{ratio}'), [aria-label*='{ratio}'], button:has(i:has-text('crop_'))").first
                if await ratio_loc.is_visible(timeout=1500):
                    await ratio_loc.click()
                    logger.info(f"Aspect ratio {ratio} selected.")
                    await self.page.wait_for_timeout(400)
                else:
                    logger.info(f"Ratio {ratio} button not explicitly visible in popup; proceeding with current default.")
        except Exception as e:
            logger.warning(f"Could not change aspect ratio: {e}")

    async def set_output_count(self, count: int = 4) -> None:
        """Configures output image count (1, 2, or 4)."""
        logger.info(f"Ensuring output count is set to {count} (x{count})...")
        try:
            badge_trigger = self.page.locator("button:has-text('Banana'), button:has-text('Nano')").first
            if await badge_trigger.is_visible(timeout=1500):
                await badge_trigger.click()
                await self.page.wait_for_timeout(600)

                count_btn = self.page.locator(f"button:has-text('x{count}'), button:has-text('{count}')").first
                if await count_btn.is_visible(timeout=1500):
                    await count_btn.click()
                    logger.info(f"Output count set to {count}.")
                    await self.page.wait_for_timeout(400)
                else:
                    # Close popup if open
                    await self.page.keyboard.press("Escape")
        except Exception as e:
            logger.warning(f"Could not change output count: {e}")

    async def upload_reference_image(self, image_path: Path) -> None:
        """Uploads a reference image to guide generation via file input or drag-and-drop."""
        logger.info(f"Uploading reference image from {image_path}...")
        try:
            file_input = self.page.locator("input[type='file'][accept*='image']").first
            if await file_input.count() > 0:
                await file_input.set_input_files(str(image_path))
                logger.info("Reference image uploaded via file input.")
                await self.page.wait_for_timeout(2000)
            else:
                logger.warning("No file input found for reference image upload.")
        except Exception as e:
            logger.warning(f"Reference image upload failed or not supported in this view: {e}")


    async def dismiss_popups(self) -> None:
        """Closes any open popovers, dropdowns or radix dialog backdrops."""
        try:
            # Press Escape to close Radix popups / dropdowns
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(200)
            # If a backdrop overlay is still open, click the canvas or press Escape again
            overlay = self.page.locator("div[data-state='open'][aria-hidden='true']").first
            if await overlay.is_visible(timeout=200):
                await self.page.keyboard.press("Escape")
        except Exception:
            pass

    async def insert_prompt(self, prompt: str) -> None:
        """Inserts the exact user prompt into the input field."""
        logger.info("Locating prompt textarea / editor...")
        await self.dismiss_popups()

        prompt_box = await self.find_element(sel.PROMPT_INPUT_SELECTORS, timeout_ms=5000)
        if not prompt_box:
            raise FlowAutomationException(
                "FLOW_PAGE_LOAD_FAILED",
                "Could not locate the prompt input field in Google Flow."
            )

        try:
            await prompt_box.click(timeout=3000)
        except Exception:
            logger.info("Click intercepted by overlay. Attempting force click & focus...")
            await self.dismiss_popups()
            await prompt_box.click(force=True)

        await prompt_box.focus()
        # Select all and delete to clear Slate editor cleanly
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")
        await self.page.wait_for_timeout(200)
        
        # Type the prompt using keyboard simulation for Slate.js compatibility
        await prompt_box.type(prompt, delay=10)
        logger.info("Prompt successfully inserted into editor.")
        await self.page.wait_for_timeout(500)


    async def click_generate(self) -> None:
        """Triggers the generation action."""
        logger.info("Locating Generate / Create button...")
        gen_btn = await self.find_element(sel.GENERATE_BUTTON_SELECTORS, timeout_ms=5000)
        if gen_btn:
            try:
                await gen_btn.click()
                logger.info("Generate button clicked.")
                await self.page.wait_for_timeout(1000)
                return
            except Exception as e:
                logger.warning(f"Error clicking generate button: {e}. Falling back to keyboard Enter.")

        logger.info("Falling back to pressing Enter in the prompt editor...")
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(1000)


    async def check_quota_or_rate_limit(self) -> None:
        """Detects visible rate limit or quota exceeded warnings."""
        for q_sel in sel.QUOTA_ERROR_SELECTORS:
            try:
                locator = self.page.locator(q_sel).first
                if await locator.is_visible(timeout=300):
                    text = await locator.inner_text()
                    raise FlowAutomationException(
                        "FLOW_RATE_LIMITED",
                        f"Google Flow rate limit or quota exceeded: {text}"
                    )
            except FlowAutomationException:
                raise
            except Exception:
                continue

    async def is_generating(self) -> bool:
        """Checks if a generation is currently active."""
        for ind_sel in sel.GENERATING_INDICATORS:
            try:
                if await self.page.locator(ind_sel).first.is_visible(timeout=200):
                    return True
            except Exception:
                continue
        return False
