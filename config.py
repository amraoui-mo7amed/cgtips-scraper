import json
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

# Image thumbnail cache (exported/imported by cache_io)
IMAGE_CACHE_DIR = DATA_DIR / "cache" / "images"

# User settings persisted next to the default data dir so they survive a
# storage-location change (the settings file itself never moves).
SETTINGS_FILE = Path(DEFAULT_DATA_DIR) / "settings.json"


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _usable_dir(path) -> "Path | None":
    """Returns the resolved directory if it can be created and written to."""
    if not path or not str(path).strip():
        return None
    try:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".cgtips_write_test"
        probe.write_text("ok")
        probe.unlink()
        return p.resolve()
    except Exception:
        return None


# Storage location: a path chosen in the app wins over the .env value.
# Always read it as `config.FEEDS_DIR` (not `from config import FEEDS_DIR`)
# so a runtime change via set_feeds_dir() is picked up everywhere.
FEEDS_DIR = (
    _usable_dir(load_settings().get("feeds_dir") or "")
    or _usable_dir(config("FEEDS_DIR", default=DEFAULT_FEEDS_DIR))
    or _usable_dir(DEFAULT_FEEDS_DIR)
    or Path(DEFAULT_FEEDS_DIR)
)


def set_feeds_dir(path) -> Path:
    """Switches the download/library directory at runtime and persists it."""
    global FEEDS_DIR
    p = _usable_dir(path)
    if p is None:
        raise ValueError(f"Directory is not writable: {path}")
    settings = load_settings()
    settings["feeds_dir"] = str(p)
    save_settings(settings)
    FEEDS_DIR = p
    return p


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
