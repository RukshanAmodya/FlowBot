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



async def main(prompt: str = None, ref_img_path: str = None):
    print("=" * 60)
    print("[INFO] Launching visible Chromium browser window...")
    print("=" * 60)

    if not prompt:
        prompt = "A cinematic cute fluffy puppy in a magical sunflower garden, 8k"
    
    # Ensure a test reference image always exists
    if not ref_img_path:
        sample_img = PROJECT_ROOT / "sample_reference.png"
        if not sample_img.exists():
            from PIL import Image
            img = Image.new('RGB', (512, 512), color=(73, 109, 137))
            img.save(str(sample_img))
        ref_img_path = str(sample_img.resolve())
        print(f"[INFO] Using test reference image: {ref_img_path}")



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
        downloader = ImageDownloader(settings.output_path)

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

        print("\n[Step 8] Waiting for Google Flow to finish generating 4 images...")
        await page.wait_for_timeout(35000)

        print("\n[SUCCESS] Done! Keeping browser open for 30s for inspection...")
        await page.wait_for_timeout(30000)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())

