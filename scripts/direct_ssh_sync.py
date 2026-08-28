"""Direct SSH / SCP session upload script using PuTTY/OpenSSH key."""
import sys
import subprocess
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROFILE_DIR = PROJECT_ROOT / "browser_profile"
PPK_KEY = Path(r"C:\Users\Rukshan Amodya\Downloads\Oracal Always Free VPS .ppk")
VPS_IP = "140.245.107.135"

print("==================================================")
print("[INFO] Direct VPS Sync via Oracle SSH Key (.ppk)")
print("==================================================")

if not PPK_KEY.exists():
    print(f"[ERROR] SSH Key not found at {PPK_KEY}")
else:
    print(f"[INFO] Found SSH Key: {PPK_KEY.name}")

# Direct HTTP 1-Click Sync to VPS API (Fastest, avoids SFTP connection blocks)
print("[INFO] Uploading session package directly to FlowBot API on VPS...")
from scripts.sync_session_to_vps import sync_session_to_vps
sync_session_to_vps(VPS_IP)

