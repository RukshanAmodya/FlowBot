"""Adapter layer abstracting interaction with Google Flow DOM."""
import asyncio
from pathlib import Path
from typing import List, Optional
from playwright.async_api import Page, Locator
from app.config import settings

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
        self.current_edit_url: Optional[str] = None


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
        """Verifies whether the current page has an active Google Flow session and logs the state."""
        try:
            url = self.page.url
            logger.info(f"Checking Google authentication state on URL: {url}...")
            
            # Check for Google Sign-in redirects
            if "accounts.google.com" in url or "signin" in url:
                logger.warning(f"Google redirect detected ({url}). Authentication required.")
                return False

            for sign_in_sel in sel.SIGN_IN_BUTTON_SELECTORS:
                if await self.page.locator(sign_in_sel).is_visible(timeout=1500):
                    logger.warning(f"Found Sign In button ({sign_in_sel}). Authentication required.")
                    return False

            logger.info("Google Authentication SUCCESS! Session is active and verified.")
            return True
        except Exception as e:
            logger.warning(f"Authentication verification notice: {e}")
            return True

    async def get_logged_in_email(self) -> Optional[str]:
        """Extracts the active Google Account email from DOM or profile Preferences."""
        try:
            # 1. Check live DOM for Google Account button tooltip/aria-label
            account_btn = self.page.locator("a[aria-label*='Google Account'], button[aria-label*='Google Account'], [aria-label*='@']").first
            if await account_btn.is_visible(timeout=1000):
                aria = await account_btn.get_attribute("aria-label") or ""
                if "@" in aria:
                    for part in aria.replace(":", " ").replace("\n", " ").split():
                        if "@" in part:
                            return part.strip("()")
                if "Google Account" in aria:
                    return aria.replace("Google Account", "").strip(": ")
        except Exception:
            pass

        # 2. Extract from Chrome Profile Preferences file
        try:
            import json
            pref_file = settings.profile_path / "Default" / "Preferences"
            if pref_file.exists():
                data = json.loads(pref_file.read_text(encoding="utf-8", errors="ignore"))
                accounts = data.get("account_info", [])
                if accounts and isinstance(accounts, list):
                    email = accounts[0].get("email")
                    if email:
                        return email
        except Exception:
            pass

        return None


    async def open_project_or_new(self) -> None:
        """Ensures the designated project workspace is open directly without creating new ones."""
        logger.info("Checking project workspace...")
        
        # Check if landed on Google Flow promotional landing page with 'Create with Google Flow' button
        create_flow_btn = self.page.locator("button:has-text('Create with Google Flow'), button:has-text('Try in Google Flow')").first
        if await create_flow_btn.is_visible(timeout=2000):
            logger.info("Found landing page entry button. Entering workspace...")
            await create_flow_btn.click()
            await self.page.wait_for_timeout(3000)

        clean_url = settings.FLOW_URL.split("#")[0]
        if "/project/" not in self.page.url:
            logger.info(f"Navigating directly to project workspace: {clean_url}...")
            await self.page.goto(clean_url, wait_until="domcontentloaded", timeout=45000)
            await self.page.wait_for_timeout(3000)

        # Check again if still on landing page
        if await create_flow_btn.is_visible(timeout=1000):
            await create_flow_btn.click()
            await self.page.wait_for_timeout(3000)

        new_proj_btn = await self.find_element(sel.NEW_PROJECT_SELECTORS, timeout_ms=2000)
        if new_proj_btn and "/project/" not in self.page.url:
            logger.info("Found 'New Project' button. Initializing project workspace...")
            await new_proj_btn.click()
            for _ in range(20):
                if "/project/" in self.page.url:
                    logger.info(f"Entered project workspace: {self.page.url}")
                    break
                await self.page.wait_for_timeout(500)
            await self.page.wait_for_timeout(3000)




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
        """Explicitly selects Nano Banana 2 model in main canvas or opened image view."""
        logger.info("Attempting to select model: Nano Banana 2 (Exact)...")
        try:
            # Check model badge (e.g. '🍌 Nano Banana Pro' or '🍌 Nano Banana 2')
            badge = self.page.locator("button:has-text('Banana'), button:has-text('Nano')").last
            if await badge.is_visible(timeout=1500):
                badge_text = await badge.inner_text()
                if "Nano Banana 2" in badge_text and "Lite" not in badge_text:
                    logger.info("Nano Banana 2 is already active.")
                    return
                
                logger.info(f"Current badge: '{badge_text}'. Clicking to switch to Nano Banana 2...")
                await badge.click()
                await self.page.wait_for_timeout(800)

            # 1. Inside the settings popup, locate the model selector dropdown
            model_selector = self.page.locator(
                "div[role='dialog'] button:has-text('Banana'), "
                "div[data-state='open'] button:has-text('Banana'), "
                "div[role='dialog'] [role='combobox'], "
                "[role='dialog'] button:has-text('Nano')"
            ).first

            if await model_selector.is_visible(timeout=2000):
                logger.info("Found model dropdown in popup. Opening options...")
                await model_selector.click()
                await self.page.wait_for_timeout(800)

            # 2. Select EXACTLY 'Nano Banana 2' (strictly avoiding 'Nano Banana Lite' or 'Pro')
            # Look for options having text 'Nano Banana 2' without 'Lite'
            model_options = await self.page.locator(
                "[role='option'], [role='menuitem'], [role='menuitemradio'], button, div[role='menu'] > div, div[data-radix-popper-content-wrapper] button"
            ).all()

            selected = False
            for opt in model_options:
                try:
                    txt = await opt.inner_text()
                    # Must contain 'Nano Banana 2' or 'Banana 2' and NOT 'Lite' or 'Pro'
                    if ("Nano Banana 2" in txt or "Banana 2" in txt) and "Lite" not in txt and "Pro" not in txt:
                        logger.info(f"Found exact Nano Banana 2 option: '{txt}'. Clicking...")
                        await opt.click()
                        selected = True
                        await self.page.wait_for_timeout(800)
                        break
                except Exception:
                    continue

            if not selected:
                # Fallback to direct locator with exact text
                exact_loc = self.page.locator("text=/^.*Nano Banana 2.*$/").first
                if await exact_loc.is_visible(timeout=1500):
                    await exact_loc.click()
                    logger.info("Clicked Nano Banana 2 via regex locator.")
                    await self.page.wait_for_timeout(600)

        except Exception as e:
            logger.info(f"Model selection notice: {e}. Continuing...")
        finally:
            # Safely close popup without closing the reference image edit view
            try:
                # Click outside or press Escape once gently
                backdrop = self.page.locator("div[data-state='open'][aria-hidden='true']").first
                if await backdrop.is_visible(timeout=300):
                    await backdrop.click(position={"x": 10, "y": 10})
                else:
                    await self.page.keyboard.press("Escape")
            except Exception:
                pass






    async def set_aspect_ratio(self, ratio: str = "9:16") -> None:
        """Configures the aspect ratio (e.g., 9:16, 16:9, 1:1, 4:3, 3:4)."""
        logger.info(f"Configuring aspect ratio to {ratio}...")
        try:
            # Model & settings trigger button (e.g. [🍌 Nano Banana 2  crop_portrait  x1])
            badge_trigger = self.page.locator("button:has-text('Banana'), button:has-text('Nano'), button:has(i:has-text('crop_'))").first
            if await badge_trigger.is_visible(timeout=1500):
                await badge_trigger.click()
                await self.page.wait_for_timeout(600)

                # Map ratio to exact UI labels (e.g., 9:16 is '9:16' or 'Portrait' or '9 : 16')
                ratio_candidates = [
                    f"button:has-text('{ratio}')",
                    f"[aria-label*='{ratio}']",
                    f"button:has-text('{ratio.replace(':', ' : ')}')",
                ]
                if ratio == "9:16":
                    ratio_candidates.extend(["button:has-text('9:16')", "button:has-text('Portrait')", "button:has(i:has-text('crop_portrait'))"])
                elif ratio == "16:9":
                    ratio_candidates.extend(["button:has-text('16:9')", "button:has-text('Landscape')", "button:has(i:has-text('crop_landscape'))"])
                elif ratio == "1:1":
                    ratio_candidates.extend(["button:has-text('1:1')", "button:has-text('Square')", "button:has(i:has-text('crop_square'))"])

                ratio_selected = False
                for r_sel in ratio_candidates:
                    ratio_loc = self.page.locator(r_sel).first
                    if await ratio_loc.is_visible(timeout=800):
                        await ratio_loc.click()
                        logger.info(f"Aspect ratio {ratio} selected using selector: {r_sel}")
                        ratio_selected = True
                        await self.page.wait_for_timeout(400)
                        break

                if not ratio_selected:
                    logger.info(f"Ratio {ratio} button not explicitly matched; proceeding with current default.")
        except Exception as e:
            logger.warning(f"Could not change aspect ratio: {e}")
        finally:
            await self.dismiss_popups()

    async def set_output_count(self, count: int = 1) -> None:
        """Configures output image count (1, 2, or 4)."""
        logger.info(f"Ensuring output count is set to {count} (x{count})...")
        try:
            badge_trigger = self.page.locator("button:has-text('Banana'), button:has-text('Nano'), button:has(i:has-text('crop_'))").first
            if await badge_trigger.is_visible(timeout=1500):
                await badge_trigger.click()
                await self.page.wait_for_timeout(600)

                count_btn = self.page.locator(f"button:has-text('x{count}'), button:has-text('{count}')").first
                if await count_btn.is_visible(timeout=1500):
                    await count_btn.click()
                    logger.info(f"Output count set to {count}.")
                    await self.page.wait_for_timeout(400)
                else:
                    await self.dismiss_popups()
        except Exception as e:
            logger.warning(f"Could not change output count: {e}")
        finally:
            await self.dismiss_popups()


    async def upload_reference_image(self, image_path: Path) -> None:
        """Uploads a reference image to Google Flow according to the exact UI flow."""
        logger.info(f"Uploading reference image from {image_path}...")
        try:
            # 1. Look for top right '+' button or prompt bar '+' button to open upload menu
            top_plus_btn = self.page.locator("header button:has(i:has-text('add')), button:has(i:has-text('add_2')), button:has(i:has-text('add'))").first
            if await top_plus_btn.is_visible(timeout=2000):
                await top_plus_btn.click()
                await self.page.wait_for_timeout(800)

            # 2. Upload file via native file input or file chooser safely
            file_input = self.page.locator("input[type='file']").first
            if await file_input.count() > 0:
                logger.info("Directly attaching file to DOM file input...")
                await file_input.set_input_files(str(image_path))
                logger.info(f"Attached file: {image_path.name}")
            else:
                upload_media_btn = self.page.locator("button:has-text('Upload media'), [role='menuitem']:has-text('Upload media'), div:has-text('Upload media')").first
                if await upload_media_btn.is_visible(timeout=2000):
                    logger.info("Clicking 'Upload media' button...")
                    try:
                        async with self.page.expect_file_chooser(timeout=3000) as fc_info:
                            await upload_media_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(str(image_path))
                        logger.info(f"Selected file via chooser: {image_path.name}")
                    except Exception:
                        logger.info("File chooser event bypassed, clicking upload media directly...")
                        await upload_media_btn.click()


            # 3. Track upload progress percentage (e.g. 7% -> 100%) and wait for full preview render
            logger.info("Tracking upload progress until 100% complete and rendered...")
            for _ in range(60):
                # Percentage indicator (e.g. 7%, 50%, 100%) in the top right corner of the uploading card
                progress_indicator = self.page.locator("*:has-text('%'), [role='progressbar']").first
                if await progress_indicator.is_visible(timeout=500):
                    p_text = await progress_indicator.inner_text()
                    logger.info(f"Upload in progress: {p_text}")
                    await self.page.wait_for_timeout(1000)
                else:
                    logger.info("Upload percentage reached 100% and completed.")
                    break

            # Buffer time for the image preview to fully replace the upload placeholder
            logger.info("Waiting for uploaded reference image preview to fully render on workspace...")
            await self.page.wait_for_timeout(4000)
            await self.dismiss_popups()

            # 4. Click the newly uploaded image at the very first position (top/leftmost item on workspace)
            logger.info("Clicking the first uploaded image card position to open image view...")
            first_image_card = self.page.locator(
                "div.sc-888a6226-1 img, div[data-testid='virtuoso-item-list'] img, main img, div[role='img']"
            ).first
            
            if await first_image_card.is_visible(timeout=6000):
                await first_image_card.click()
                logger.info("Clicked first image card. Verifying and remembering transition to image edit URL (/edit/)...")
                
                # Check and remember URL transition to /project/.../edit/...
                for _ in range(12):
                    if "/edit/" in self.page.url:
                        self.current_edit_url = self.page.url
                        logger.info(f"Remembered image edit URL: {self.current_edit_url}")
                        break
                    await self.page.wait_for_timeout(500)
                
                await self.page.wait_for_timeout(1500)
            else:
                logger.warning("First canvas image card not found; checking if already inside /edit/...")
                if "/edit/" in self.page.url:
                    self.current_edit_url = self.page.url
                    logger.info(f"Already in image edit view, remembered URL: {self.current_edit_url}")
                else:
                    canvas = self.page.locator("div[data-testid='virtuoso-scroller']").first
                    if await canvas.is_visible(timeout=2000):
                        await canvas.click(position={"x": 200, "y": 200})
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
        """Inserts the exact user prompt into the active prompt input field (supporting image edit view)."""
        logger.info(f"Inserting prompt into active view (URL: {self.page.url})...")
        
        # High priority visible prompt editor selectors
        editor_selectors = [
            "div[role='textbox'][data-slate-editor='true']",
            "div[data-slate-editor='true']",
            "div.sc-1c9f7009-0",
            "[contenteditable='true']:not([aria-hidden='true'])",
            "div.sc-5c3af813-0 [role='textbox']",
            "div[role='textbox']:not([aria-hidden='true'])",
            "textarea:not([name*='recaptcha']):not([id*='recaptcha'])",
        ]

        prompt_box = None
        for sel_item in editor_selectors:
            try:
                elements = self.page.locator(sel_item)
                count = await elements.count()
                for i in range(count - 1, -1, -1):
                    cand = elements.nth(i)
                    if await cand.is_visible(timeout=500):
                        prompt_box = cand
                        break
                if prompt_box:
                    break
            except Exception:
                continue

        if not prompt_box:
            # Try clicking on bottom prompt container
            container = self.page.locator("div.sc-5c3af813-0, div.sc-5c3af813-10, div:has-text('Describe'), footer, [data-slate-editor='true']").first
            if await container.is_visible(timeout=1500):
                await container.click()
                await self.page.wait_for_timeout(300)
                prompt_box = self.page.locator("div[data-slate-editor='true'], [contenteditable='true']").last

        if not prompt_box:
            raise FlowAutomationException(
                "FLOW_PAGE_LOAD_FAILED",
                "Could not locate the prompt input field in Google Flow."
            )

        try:
            await prompt_box.click(timeout=1500)
        except Exception:
            await prompt_box.click(force=True)

        try:
            await prompt_box.focus()
        except Exception:
            pass

        await self.page.wait_for_timeout(300)
        
        # Type prompt using keyboard simulation
        try:
            await prompt_box.type(f" {prompt}", delay=15)
        except Exception:
            await self.page.keyboard.type(f" {prompt}", delay=15)

        logger.info(f"Prompt successfully inserted into prompt textbox: '{prompt}'")

        await self.page.wait_for_timeout(600)




    async def click_generate(self) -> None:
        """Triggers the generation action (arrow button or Enter)."""
        logger.info("Locating Generate / Arrow button...")
        gen_btn_selectors = [
            "button:has(i:has-text('arrow_forward'))",
            "button:has(i:has-text('send'))",
            "button:has-text('Create')",
            "button:has-text('Generate')",
            "[aria-label*='Create']",
            "[aria-label*='Generate']",
            "[aria-label*='Submit']"
        ]
        
        for g_sel in gen_btn_selectors:
            btn = self.page.locator(g_sel).last
            if await btn.is_visible(timeout=1500):
                try:
                    await btn.click()
                    logger.info(f"Generation triggered via button ({g_sel}).")
                    await self.page.wait_for_timeout(1000)
                    return
                except Exception:
                    pass

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
