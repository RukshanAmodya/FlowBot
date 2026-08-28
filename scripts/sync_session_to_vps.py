"""Script to 1-click sync local authenticated Google session to VPS server."""
import sys
import os
import zipfile
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_ROOT / "browser_profile"

def sync_session_to_vps(vps_ip: str, vps_port: int = 8000):
    if not PROFILE_DIR.exists():
        print(f"[ERROR] Local browser_profile directory does not exist at {PROFILE_DIR}")
        return

    print(f"==================================================")
    print(f"📦 Packaging local Google Flow session...")
    print(f"==================================================")

    zip_path = PROJECT_ROOT / "browser_profile_sync.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROFILE_DIR):
            for file in files:
                file_full = Path(root) / file
                arcname = file_full.relative_to(PROFILE_DIR)
                try:
                    zipf.write(file_full, arcname)
                except Exception:
                    pass

    print(f"[SUCCESS] Session packaged ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"🚀 Uploading session directly to VPS: http://{vps_ip}:{vps_port}/api/v1/auth/upload-session ...")

    url = f"http://{vps_ip}:{vps_port}/api/v1/auth/upload-session"
    try:
        with open(zip_path, "rb") as f:
            files = {"file": ("browser_profile.zip", f, "application/zip")}
            response = httpx.post(url, files=files, timeout=60.0)

        if response.status_code == 200:
            print("==================================================")
            print("🎉 SUCCESS! Google Login Session successfully synced to VPS!")
            print(f"Now your VPS ({vps_ip}) is 100% authenticated and ready to generate images!")
            print("==================================================")
        else:
            print(f"[FAILED] Server returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Could not connect to VPS: {e}")
    finally:
        if zip_path.exists():
            zip_path.unlink()

if __name__ == "__main__":
    vps_ip = sys.argv[1] if len(sys.argv) > 1 else "140.245.107.135"
    sync_session_to_vps(vps_ip)
