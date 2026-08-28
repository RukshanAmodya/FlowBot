"""Interactive browser launcher for manual Google Flow authentication."""
import asyncio
from playwright.async_api import async_playwright
from app.config import settings
from app.services.flow_adapter import GoogleFlowAdapter

async def main():
    print("=" * 65)
    print("GOOGLE FLOW - ONE-TIME MANUAL AUTHENTICATION SETUP")
    print("=" * 65)
    print(f"Profile Directory: {settings.profile_path.resolve()}")
    print(f"Opening Flow URL:  {settings.FLOW_URL}")
    print("\nInstructions:")
    print("1. A browser window will open.")
    print("2. Sign in to your Google Account manually.")
    print("3. Ensure Google Flow loads and your account avatar is visible.")
    print("4. Return here and press ENTER to finalize and save the session.")
    print("=" * 65)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )

        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        print("\nNavigating to Google Flow...")
        try:
            await page.goto(settings.FLOW_URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"Initial navigation notice: {e}")

        await asyncio.to_thread(input, "\n--> Press ENTER once you have fully signed in to Google Flow... ")

        adapter = GoogleFlowAdapter(page)
        is_authenticated = await adapter.check_authenticated()

        if is_authenticated:
            print("\n[SUCCESS] Active Google Flow session detected and verified!")
        else:
            print("\n[WARNING] Sign-in marker not clearly detected. Ensure you are signed in before running API.")

        await context.close()
        print("Browser context closed. Persistent profile updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
