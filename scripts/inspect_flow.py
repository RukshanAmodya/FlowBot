"""Flow UI discovery and inspection tool."""
import asyncio
import datetime
from playwright.async_api import async_playwright
from app.config import settings

async def main():
    print("=" * 60)
    print("GOOGLE FLOW - UI DISCOVERY & SELECTOR INSPECTION TOOL")
    print("=" * 60)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=False,
            viewport={"width": 1440, "height": 900}
        )

        page = context.pages[0] if context.pages else await context.new_page()
        print(f"Navigating to {settings.FLOW_URL}...")
        await page.goto(settings.FLOW_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)

        buttons = await page.locator("button, [role='button']").all()
        print(f"\nDiscovered {len(buttons)} button elements:")
        for idx, btn in enumerate(buttons[:25], 1):
            try:
                text = (await btn.inner_text()).strip().replace("\n", " ")
                aria = await btn.get_attribute("aria-label") or ""
                print(f"  [{idx}] Text: '{text}' | Aria: '{aria}'")
            except Exception:
                pass

        inputs = await page.locator("textarea, input, [contenteditable='true']").all()
        print(f"\nDiscovered {len(inputs)} input/textarea elements:")
        for idx, inp in enumerate(inputs[:10], 1):
            try:
                placeholder = await inp.get_attribute("placeholder") or ""
                aria = await inp.get_attribute("aria-label") or ""
                tag = await inp.evaluate("el => el.tagName")
                print(f"  [{idx}] Tag: <{tag}> | Placeholder: '{placeholder}' | Aria: '{aria}'")
            except Exception:
                pass

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_file = settings.screenshot_path / f"inspect_{timestamp}.png"
        html_file = settings.screenshot_path / f"inspect_{timestamp}.html"
        await page.screenshot(path=str(screenshot_file), full_page=True)
        content = await page.content()
        html_file.write_text(content, encoding="utf-8")

        print(f"\nSaved snapshot to:")
        print(f"  - Screenshot: {screenshot_file}")
        print(f"  - DOM HTML:   {html_file}")
        print("=" * 60)

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
