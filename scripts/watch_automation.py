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
        prompt = "Add a cute, fluffy golden retriever puppy sitting happily in the water right next to this girl, highly detailed, realistic, cinematic lighting, 8k"
    
    # Allow user to specify image path interactively or use specified Downloads image
    if not ref_img_path:
        default_downloads_img = Path(r"C:\Users\Rukshan Amodya\Downloads\38e1213cbf7935579e3234b266c13c42.jpg")
        if default_downloads_img.exists():
            ref_img_path = str(default_downloads_img.resolve())
        else:
            user_img_input = input("Enter path to your reference image [or press ENTER to search for images]: ").strip().strip('"')
            if user_img_input and Path(user_img_input).exists():
                ref_img_path = str(Path(user_img_input).resolve())

        else:
            # Check for any realistic test images in the workspace
            found_images = list(PROJECT_ROOT.glob("*.jpg")) + list(PROJECT_ROOT.glob("*.png")) + list(PROJECT_ROOT.glob("generated/**/*.png"))
            # Filter out sample_reference.png if possible
            real_images = [img for img in found_images if img.name != "sample_reference.png"]
            if real_images:
                ref_img_path = str(real_images[0].resolve())
            elif found_images:
                ref_img_path = str(found_images[0].resolve())
            else:
                sample_img = PROJECT_ROOT / "sample_reference.png"
                if not sample_img.exists():
                    from PIL import Image
                    img = Image.new('RGB', (512, 512), color=(73, 109, 137))
                    img.save(str(sample_img))
                ref_img_path = str(sample_img.resolve())

    print(f"[INFO] Using reference image: {ref_img_path}")




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

