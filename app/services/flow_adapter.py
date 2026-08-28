"""Adapter layer abstracting interaction with Google Flow DOM."""
import asyncio
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
        """Ensures an active project/workspace is open for generation."""
        logger.info("Checking for open project or creating a new one...")
        new_proj_btn = await self.find_element(sel.NEW_PROJECT_SELECTORS, timeout_ms=4000)
        if new_proj_btn:
            logger.info("Found 'New Project' button. Clicking to initialize project.")
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
        """Configures the aspect ratio."""
        logger.info(f"Configuring aspect ratio to {ratio}...")
        options = sel.ASPECT_RATIO_OPTIONS.get(ratio)
        if not options:
            logger.warning(f"Unknown aspect ratio {ratio}, skipping custom ratio selection.")
            return

        dropdown = await self.find_element(sel.ASPECT_RATIO_DROPDOWN_SELECTORS, timeout_ms=2000)
        if dropdown:
            await dropdown.click()
            await self.page.wait_for_timeout(500)

        option_elem = await self.find_element(options, timeout_ms=2000)
        if option_elem:
            await option_elem.click()
            logger.info(f"Aspect ratio {ratio} selected.")
        else:
            logger.info(f"Aspect ratio option for {ratio} not directly interactive; proceeding with default.")

    async def set_output_count(self, count: int = 4) -> None:
        """Configures output image count."""
        if count != 4:
            raise FlowAutomationException(
                "OUTPUT_COUNT_NOT_SUPPORTED",
                f"Requested output count {count} is not supported. Exactly 4 outputs required."
            )
        
        logger.info("Ensuring output count is set to 4...")
        dropdown = await self.find_element(sel.OUTPUT_COUNT_DROPDOWN_SELECTORS, timeout_ms=2000)
        if dropdown:
            await dropdown.click()
            await self.page.wait_for_timeout(500)
            opt4 = await self.find_element(sel.OUTPUT_COUNT_4_SELECTORS, timeout_ms=2000)
            if opt4:
                await opt4.click()
                logger.info("Output count 4 selected from dropdown.")

    async def insert_prompt(self, prompt: str) -> None:
        """Inserts the exact user prompt into the input field."""
        logger.info("Locating prompt textarea / editor...")
        prompt_box = await self.find_element(sel.PROMPT_INPUT_SELECTORS, timeout_ms=5000)
        if not prompt_box:
            raise FlowAutomationException(
                "FLOW_PAGE_LOAD_FAILED",
                "Could not locate the prompt input field in Google Flow."
            )

        await prompt_box.click()
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
