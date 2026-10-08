"""
Persistent Application Settings Manager for CGTips 3D Desktop.
Handles Client Agent executable path and Multi-Destination Disk paths.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR

logger = logging.getLogger("settings_manager")

SETTINGS_FILE = DATA_DIR / "settings.json"


class SettingsManager:
    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = Path(settings_file or SETTINGS_FILE)
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    DEFAULT_API_URL = "https://loftdesign.bilnov.com/api"

    def _load(self) -> Dict[str, Any]:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return {
                            "client_agent_path": data.get("client_agent_path", ""),
                            "copy_destinations": [
                                p for p in data.get("copy_destinations", []) if isinstance(p, str) and p.strip()
                            ],
                            "api_url": data.get("api_url", self.DEFAULT_API_URL).rstrip("/"),
                            "api_username": data.get("api_username", ""),
                            "api_password": data.get("api_password", ""),
                            "prefer_gdrive_api": bool(data.get("prefer_gdrive_api", False)),
                            "gdrive_user_email": str(data.get("gdrive_user_email", "")),
                            "gdrive_user_name": str(data.get("gdrive_user_name", "")),
                        }
            except Exception as e:
                logger.warning("Failed to load settings from %s: %s", self.settings_file, e)
        return {
            "client_agent_path": "",
            "copy_destinations": [],
            "api_url": self.DEFAULT_API_URL,
            "api_username": "",
            "api_password": "",
            "prefer_gdrive_api": False,
            "gdrive_user_email": "",
            "gdrive_user_name": "",
        }

    def _save(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save settings to %s: %s", self.settings_file, e)

    def get_client_agent_path(self) -> str:
        with self._lock:
            return self._data.get("client_agent_path", "")

    def set_client_agent_path(self, path: str):
        with self._lock:
            self._data["client_agent_path"] = str(path).strip()
            self._save()

    def get_copy_destinations(self) -> List[str]:
        with self._lock:
            return list(self._data.get("copy_destinations", []))

    def set_copy_destinations(self, paths: List[str]):
        with self._lock:
            cleaned = []
            for p in paths:
                s = str(p).strip()
                if s and s not in cleaned:
                    cleaned.append(s)
            self._data["copy_destinations"] = cleaned
            self._save()

    def add_copy_destination(self, path: str) -> bool:
        with self._lock:
            p = str(path).strip()
            if not p:
                return False
            dests = self._data.get("copy_destinations", [])
            if p not in dests:
                dests.append(p)
                self._data["copy_destinations"] = dests
                self._save()
                return True
            return False

    def remove_copy_destination(self, path: str) -> bool:
        with self._lock:
            dests = self._data.get("copy_destinations", [])
            if path in dests:
                dests.remove(path)
                self._data["copy_destinations"] = dests
                self._save()
                return True
            return False

    def clear_copy_destinations(self):
        with self._lock:
            self._data["copy_destinations"] = []
            self._save()

    # --- Loft Design API Settings ---

    def get_api_url(self) -> str:
        with self._lock:
            return self._data.get("api_url", self.DEFAULT_API_URL)

    def set_api_url(self, url: str):
        with self._lock:
            cleaned = str(url).strip().rstrip("/") if str(url).strip() else self.DEFAULT_API_URL
            self._data["api_url"] = cleaned
            self._save()

    def get_api_username(self) -> str:
        with self._lock:
            return self._data.get("api_username", "")

    def set_api_username(self, username: str):
        with self._lock:
            self._data["api_username"] = str(username).strip()
            self._save()

    def get_api_password(self) -> str:
        with self._lock:
            return self._data.get("api_password", "")

    def set_api_password(self, password: str):
        with self._lock:
            self._data["api_password"] = str(password)
            self._save()

    def get_api_config(self) -> Dict[str, str]:
        with self._lock:
            url_val = self._data.get("api_url", self.DEFAULT_API_URL)
            return {
                "api_url": url_val,
                "url": url_val,
                "username": self._data.get("api_username", ""),
                "password": self._data.get("api_password", ""),
            }

    def set_api_config(self, url: str, username: str, password: str):
        with self._lock:
            cleaned_url = str(url).strip().rstrip("/") if str(url).strip() else self.DEFAULT_API_URL
            self._data["api_url"] = cleaned_url
            self._data["api_username"] = str(username).strip()
            self._data["api_password"] = str(password)
            self._save()

    # --- Google Drive Settings ---

    def get_prefer_gdrive_api(self) -> bool:
        with self._lock:
            return bool(self._data.get("prefer_gdrive_api", False))

    def set_prefer_gdrive_api(self, prefer: bool):
        with self._lock:
            self._data["prefer_gdrive_api"] = bool(prefer)
            self._save()

    def get_gdrive_user_info(self) -> Dict[str, str]:
        with self._lock:
            return {
                "email": self._data.get("gdrive_user_email", ""),
                "name": self._data.get("gdrive_user_name", ""),
            }

    def set_gdrive_user_info(self, email: str, name: str):
        with self._lock:
            self._data["gdrive_user_email"] = str(email).strip()
            self._data["gdrive_user_name"] = str(name).strip()
            self._save()


# Singleton instance
settings_manager = SettingsManager()

