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



async def main(prompt: str = None, ref_img_path: str = None, aspect_ratio: str = "9:16", count: int = 1):
    print("=" * 65)
    print("GOOGLE FLOW - LIVE AUTOMATION INSPECTION")
    print("=" * 65)

    if not prompt:
        prompt = "Create a stunning, highly detailed portrait matching the style and character, 8k resolution, cinematic lighting"

    
    if not ref_img_path:
        default_downloads_img = Path(r"C:\Users\Rukshan Amodya\Downloads\38e1213cbf7935579e3234b266c13c42.jpg")
        if default_downloads_img.exists():
            ref_img_path = str(default_downloads_img.resolve())

    print(f"[INFO] Prompt:       {prompt}")
    print(f"[INFO] Aspect Ratio: {aspect_ratio}")
    print(f"[INFO] Output Count: {count}")
    print(f"[INFO] Reference:    {ref_img_path}")
    print("[INFO] Launching visible Chrome browser (Slow-Mo mode for clear visibility)...")
    print("=" * 65)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=False,
            channel="chrome",  # Directly launches your installed Google Chrome application
            slow_mo=800,  # 800ms delay between actions so you can watch everything live!
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )


        page = context.pages[0] if context.pages else await context.new_page()
        from app.services.flow_generator import FlowGeneratorService
        generator = FlowGeneratorService(page)

        gen_id = "live_watch_session"
        img_b64 = None
        if ref_img_path and Path(ref_img_path).exists():
            import base64
            with open(ref_img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

        print("\n--> Starting complete generation lifecycle with live browser view...")
        images = await generator.execute_generation(
            prompt=prompt,
            generation_id=gen_id,
            count=count,
            aspect_ratio=aspect_ratio,
            reference_image_base64=img_b64
        )

        print("\n" + "=" * 65)
        print(f"[SUCCESS] Generation complete! Downloaded {len(images)} images:")
        for idx, img in enumerate(images, start=1):
            print(f"  [{idx}] {img}")
        print("=" * 65)

        print("\nKeeping browser window open for 15 seconds so you can inspect the final canvas...")
        await page.wait_for_timeout(15000)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())


