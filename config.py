import socket
import os
import sys
import shutil
from pathlib import Path
from decouple import config

# Ensure reliable Cloudflare Anycast IP resolution for CGTips domains
# across regions where local DNS returns unreachable edge IPs (causing HTTP timeouts)
_CGTIPS_HOSTS = ("sketchup.cgtips.org", "cgtips.org", "www.cgtips.org")
_CGTIPS_FALLBACK_IP = "104.21.74.130"

_ORIG_GETADDRINFO = socket.getaddrinfo

def _cgtips_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host in _CGTIPS_HOSTS:
        return _ORIG_GETADDRINFO(_CGTIPS_FALLBACK_IP, port, family, type, proto, flags)
    return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)

socket.getaddrinfo = _cgtips_getaddrinfo

BASE_DIR = Path(__file__).resolve().parent

# Base URLs
BASE_URL = config("BASE_URL", default="https://sketchup.cgtips.org/").rstrip("/") + "/"
USER_AGENT = config(
    "USER_AGENT",
    default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
)

# Browser Configuration
HEADLESS = config("HEADLESS", default="true").lower() in ("true", "1", "yes")
BRAVE_PATH = config("BRAVE_PATH", default="")
CHROME_PATH = config("CHROME_PATH", default="")

# Data and Storage Paths
if getattr(sys, "frozen", False):
    _BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    if sys.platform == "darwin":
        _USER_DATA = Path.home() / "Library" / "Application Support" / "CGTips 3D"
    elif sys.platform == "win32":
        _USER_DATA = Path(os.environ.get("APPDATA", str(Path.home()))) / "CGTips 3D"
    else:
        _USER_DATA = Path.home() / ".cgtips"
    _USER_DATA.mkdir(parents=True, exist_ok=True)
    DEFAULT_DATA_DIR = str(_USER_DATA / "data")
    DEFAULT_FEEDS_DIR = str(Path.home() / "Downloads" / "CGTips_Models")

    # Pre-populate bundled categories if not already in user data
    bundled_data = _BUNDLE_DIR / "data"
    user_data_path = Path(DEFAULT_DATA_DIR)
    user_data_path.mkdir(parents=True, exist_ok=True)
    if bundled_data.exists():
        for item in ["categories.json", "selected_feeds.json"]:
            src = bundled_data / item
            dst = user_data_path / item
            if src.exists() and not dst.exists():
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass
else:
    DEFAULT_DATA_DIR = str(BASE_DIR / "data")
    DEFAULT_FEEDS_DIR = str(BASE_DIR / "feeds")

DATA_DIR = Path(config("DATA_DIR", default=DEFAULT_DATA_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

FEEDS_DIR = Path(config("FEEDS_DIR", default=DEFAULT_FEEDS_DIR))
FEEDS_DIR.mkdir(parents=True, exist_ok=True)

# Helper for locating data files in data/ or root directory
def _resolve_data_file(filename: str) -> Path:
    data_file = DATA_DIR / filename
    if data_file.exists():
        return data_file
    root_file = BASE_DIR / filename
    if root_file.exists():
        return root_file
    if getattr(sys, "frozen", False):
        bundle_file = Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "data" / filename
        if bundle_file.exists():
            return bundle_file
    return data_file

CATEGORIES_FILE = _resolve_data_file("categories.json")
SELECTED_FEEDS_FILE = _resolve_data_file("selected_feeds.json")
CREDENTIALS_FILE = _resolve_data_file("credentials.json")
TOKEN_FILE = _resolve_data_file("token.pickle")

# Web Server Settings
SERVER_HOST = config("HOST", default="0.0.0.0")
SERVER_PORT = int(config("PORT", default=8000))
