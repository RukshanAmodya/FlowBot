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
        """Explicitly selects Nano Banana 2 model if not already selected."""
        logger.info("Attempting to select model: Nano Banana 2...")
        try:
            # Check if badge already shows Nano Banana 2
            badge = self.page.locator("button:has-text('Banana'), button:has-text('Nano')").first
            if await badge.is_visible(timeout=1500):
                badge_text = await badge.inner_text()
                if "Nano Banana 2" in badge_text:
                    logger.info("Nano Banana 2 is already selected on the badge.")
                    return

            dropdown = await self.find_element(sel.MODEL_DROPDOWN_SELECTORS, timeout_ms=2000)
            if dropdown:
                await dropdown.click()
                await self.page.wait_for_timeout(800)

            model_option = await self.find_element(sel.NANO_BANANA_2_SELECTORS, timeout_ms=3000)
            if model_option:
                await model_option.click()
                logger.info("Successfully selected Nano Banana 2.")
                await self.page.wait_for_timeout(800)
            else:
                logger.info("Nano Banana 2 menu option not explicit; continuing with active model.")
        except Exception as e:
            logger.info(f"Model selection notice: {e}. Continuing...")


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
        """Uploads a reference image to Google Flow according to the exact UI flow."""
        logger.info(f"Uploading reference image from {image_path}...")
        try:
            # 1. Look for top right '+' button or prompt bar '+' button to open upload menu
            top_plus_btn = self.page.locator("header button:has(i:has-text('add')), button:has(i:has-text('add_2')), button:has(i:has-text('add'))").first
            if await top_plus_btn.is_visible(timeout=2000):
                await top_plus_btn.click()
                await self.page.wait_for_timeout(800)

            # 2. Click 'Upload media' from dropdown/dialog menu using expect_file_chooser
            upload_media_btn = self.page.locator("button:has-text('Upload media'), [role='menuitem']:has-text('Upload media'), div:has-text('Upload media')").first
            if await upload_media_btn.is_visible(timeout=2500):
                logger.info("Clicking 'Upload media' and choosing file...")
                async with self.page.expect_file_chooser(timeout=6000) as fc_info:
                    await upload_media_btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(str(image_path))
                logger.info(f"Selected file: {image_path.name}")
            else:
                # Fallback directly to native input[type=file]
                file_input = self.page.locator("input[type='file']").first
                if await file_input.count() > 0:
                    await file_input.set_input_files(str(image_path))
                    logger.info("File uploaded via fallback file input.")

            # 3. Track upload progress percentage (e.g. 7% -> 100%)
            logger.info("Tracking upload progress until 100% complete...")
            for _ in range(40):
                # Check for upload percentage indicator (e.g. "7%", "100%", progressbar)
                progress_indicator = self.page.locator("*:has-text('%'), [role='progressbar']").first
                if await progress_indicator.is_visible(timeout=500):
                    p_text = await progress_indicator.inner_text()
                    logger.info(f"Upload in progress: {p_text}")
                    await self.page.wait_for_timeout(1000)
                else:
                    break

            await self.page.wait_for_timeout(3000)
            await self.dismiss_popups()

            # 4. Click the newly uploaded image card on the workspace canvas to open it and activate its prompt box!
            logger.info("Opening the uploaded image card on workspace...")
            image_card = self.page.locator("div.sc-888a6226-1 img, div[data-testid='virtuoso-item-list'] img, main img, div[role='img']").first
            if await image_card.is_visible(timeout=4000):
                await image_card.click()
                logger.info("Successfully clicked and opened uploaded image card.")
                await self.page.wait_for_timeout(1200)
            else:
                logger.info("Canvas image card clicked or already active.")
        except Exception as e:
            logger.warning(f"Reference image upload workflow error: {e}")
            await self.dismiss_popups()





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
        
        # Type the prompt using keyboard simulation for Slate.js compatibility
        await prompt_box.type(f" {prompt}", delay=10)
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
