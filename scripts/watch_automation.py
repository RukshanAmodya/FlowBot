import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright
from app.config import settings
from app.services.flow_adapter import GoogleFlowAdapter
from app.services.image_downloader import ImageDownloader



async def main():
    print("=" * 60)
    print("🚀 Launching visible Chromium browser window...")
    print("=" * 60)

    prompt = input("\nEnter prompt to test [or press ENTER for default]: ").strip()
    if not prompt:
        prompt = "A cute fluffy golden retriever puppy in a field of sunflowers, 8k photo"

    ref_img_path = input("Enter path to a reference image [or press ENTER to skip]: ").strip()

    async with async_playwright() as p:
        # Launch visible browser with delay so you can watch everything step by step
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=False,
            slow_mo=800,  # 800ms delay between actions so you can clearly see every click and typing!
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.pages[0] if context.pages else await context.new_page()
        adapter = GoogleFlowAdapter(page)
        downloader = ImageDownloader()

        print("\n[Step 1] Navigating to Google Flow...")
        await page.goto("https://labs.google/fx/tools/flow", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        print("[Step 2] Checking project workspace...")
        await adapter.open_project_or_new()

        print("[Step 3] Selecting Image mode & Model (Nano Banana 2)...")
        await adapter.select_image_mode()
        await adapter.select_nano_banana_2()

        print("[Step 4] Configuring Aspect Ratio (16:9) and Outputs (4)...")
        await adapter.set_aspect_ratio("16:9")
        await adapter.set_output_count(4)

        if ref_img_path and Path(ref_img_path).exists():
            print(f"[Step 5] Uploading reference image: {ref_img_path}...")
            await adapter.upload_reference_image(Path(ref_img_path))

        print(f"[Step 6] Typing prompt: '{prompt}'...")
        await adapter.insert_prompt(prompt)

        print("[Step 7] Clicking Create / Generate button...")
        await adapter.click_generate()

        print("\n⏳ [Step 8] Waiting for Google Flow to finish generating 4 images...")
        # Wait and observe
        await page.wait_for_timeout(35000)

        print("\n🎉 Done! The browser will stay open for 30 seconds so you can inspect everything.")
        await page.wait_for_timeout(30000)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
