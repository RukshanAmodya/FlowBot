"""Browser session and persistent context lifecycle manager."""
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from app.config import settings
from app.utils.logger import logger
from app.services.flow_adapter import GoogleFlowAdapter, FlowAutomationException

class BrowserSessionManager:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.lock = asyncio.Lock()
        self.current_generation_id: Optional[str] = None

    async def get_or_create_context(self) -> Page:
        """Initializes or retrieves the active persistent browser page."""
        if self._page and not self._page.is_closed():
            return self._page

        logger.info(f"Launching persistent Playwright browser context at {settings.profile_path}...")
        self._playwright = await async_playwright().start()
        
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=settings.HEADLESS,
            slow_mo=50 if settings.HEADLESS else 100,
            viewport=None if not settings.HEADLESS else {"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox"
            ]
        )




        pages = self._context.pages
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._context.new_page()

        return self._page

    async def check_authenticated(self) -> bool:
        """Verifies if Google Flow is actively authenticated."""
        try:
            page = await self.get_or_create_context()
            if settings.FLOW_URL not in page.url:
                await page.goto(settings.FLOW_URL, wait_until="domcontentloaded", timeout=30000)
            adapter = GoogleFlowAdapter(page)
            return await adapter.check_authenticated()
        except Exception as e:
            logger.warning(f"Authentication verification check encountered: {e}")
            return False

    async def is_running(self) -> bool:
        """Checks if browser page is currently active."""
        return self._page is not None and not self._page.is_closed()

    async def close(self) -> None:
        """Gracefully shuts down browser session."""
        logger.info("Closing browser context...")
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Exception during browser close: {e}")
        finally:
            self._page = None
            self._context = None
            self._playwright = None

session_manager = BrowserSessionManager()
