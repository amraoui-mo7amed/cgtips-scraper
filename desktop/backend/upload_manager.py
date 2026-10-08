"""
Upload Manager for CGTips 3D Desktop.
Handles publishing scraped 3D model articles and gallery renders to
Loft Design Services REST API (https://loftdesign.bilnov.com/api/gallery/upload)
via authenticated HTTP Basic requests. Supports scoping by article, category,
subcategory, custom selection, or entire library.
"""

import base64
import logging
import mimetypes
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from .library import LibraryManager, library_manager
from .settings_manager import settings_manager
from .scraper_service import FEEDS_DIR

logger = logging.getLogger("upload_manager")


class UploadManager:
    """Manages publishing 3D articles and renders to Loft Design Services REST API."""

    def __init__(self, library_mgr: Optional[LibraryManager] = None):
        self.library = library_mgr or library_manager

    def test_connection(
        self,
        api_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Tests connectivity and authentication with Loft Design Services API.
        Returns (success: bool, message: str).
        """
        url = (api_url or settings_manager.get_api_url()).rstrip("/")
        user = username if username is not None else settings_manager.get_api_username()
        pwd = password if password is not None else settings_manager.get_api_password()

        if not url:
            return False, "API URL is required"
        if not user or not pwd:
            return False, "Username and password are required for API authentication"

        base_api = url if url.endswith("/api") else f"{url}/api"
        test_endpoint = f"{base_api}/gallery/items"
        try:
            auth = (user, pwd)
            resp = requests.get(test_endpoint, auth=auth, params={"limit": 1}, timeout=12)

            if resp.status_code == 200:
                return True, "Successfully connected and authenticated with Loft Design API"
            elif resp.status_code in (401, 403):
                detail = ""
                try:
                    data = resp.json()
                    detail = data.get("detail") or data.get("message") or ""
                except Exception:
                    pass
                msg = f"Authentication failed (HTTP {resp.status_code})"
                if detail:
                    msg += f": {detail}"
                return False, msg
            else:
                return False, f"Server responded with HTTP {resp.status_code}: {resp.text[:120]}"

        except requests.exceptions.Timeout:
            return False, "Connection timed out while reaching Loft Design server"
        except requests.exceptions.ConnectionError:
            return False, f"Could not connect to server at {url}. Please check URL and network."
        except Exception as exc:
            return False, f"Connection error: {str(exc)}"

    def upload_articles(
        self,
        scope: str = "all",
        target: Any = None,
        api_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        progress_cb: Optional[Callable[[int, int, str, str, float], None]] = None,
        log_cb: Optional[Callable[[str], None]] = None,
        stop_event: Optional[threading.Event] = None,
        library_mgr: Optional[LibraryManager] = None,
    ) -> Dict[str, Any]:
        """
        Uploads articles and renders matching scope to Loft Design gallery API.
        scope: "article" | "subcategory" | "category" | "all" | "custom"
        target:
          - for "article": folder_path
          - for "subcategory": {"category": ..., "subcategory": ...}
          - for "category": category_name
          - for "custom": list of folder_paths
        """
        def _log(msg: str):
            if log_cb:
                try:
                    log_cb(msg)
                except RuntimeError:
                    pass
            logger.info(msg)

        lib = library_mgr or self.library
        base_feeds = lib.base_dir.resolve()

        url = (api_url or settings_manager.get_api_url()).rstrip("/")
        user = username if username is not None else settings_manager.get_api_username()
        pwd = password if password is not None else settings_manager.get_api_password()

        if not user or not pwd:
            _log("✗ Upload aborted: API username and password must be configured in Settings.")
            return {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0, "cancelled": False, "error": "Missing credentials"}

        base_api = url if url.endswith("/api") else f"{url}/api"
        upload_endpoint = f"{base_api}/gallery/upload"
        _log(f"=== Starting Article Upload to Loft Design ===")
        _log(f"API Endpoint: {upload_endpoint}")
        _log(f"User: {user}")

        # Resolve articles based on scope
        if scope == "custom" and isinstance(target, (list, tuple)):
            all_articles = lib.scan_library().get("items", [])
            folder_set = set(t.get("folder_path", t) if isinstance(t, dict) else str(t) for t in target)
            articles = [it for it in all_articles if (it["folder_path"] in folder_set or it["id"] in folder_set)]
        elif scope == "article":
            articles = lib.get_articles_by_scope(scope="article", target=target)
        else:
            articles = lib.get_articles_by_scope(scope=scope, target=target)

        total_targeted = len(articles)
        if total_targeted == 0:
            _log(f"No articles found for upload with scope '{scope}'.")
            return {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0, "cancelled": False}

        _log(f"Found {total_targeted} article(s) to process for upload.\n")

        auth = (user, pwd)
        succeeded = 0
        failed = 0
        skipped = 0
        cancelled = False

        for idx, item in enumerate(articles):
            if stop_event and stop_event.is_set():
                _log("Upload stopped by user.")
                cancelled = True
                break

            title = item.get("title", "Article")
            folder_rel = item.get("folder_path", "")
            cat_name = item.get("category", "General")
            sub_name = item.get("subcategory", "") or "General"
            article_dir = (base_feeds / folder_rel).resolve()

            pct = (idx / total_targeted) * 100.0
            if progress_cb:
                try:
                    progress_cb(idx + 1, total_targeted, title, f"Uploading {idx + 1}/{total_targeted}", pct)
                except RuntimeError:
                    pass

            _log(f"--- [{idx + 1}/{total_targeted}] Uploading: {title} ---")
            _log(f"Space: '{cat_name}' • Category: '{sub_name}'")

            if not article_dir.exists():
                _log(f"  ✗ Local folder not found: {folder_rel}")
                failed += 1
                continue

            # Find local images for this article
            img_files = [
                f for f in article_dir.iterdir()
                if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
            ]
            # Natural sort images
            img_files.sort(key=lambda p: (len(p.name), p.name))

            if not img_files:
                _log(f"  ⚠️ No images found in '{folder_rel}', skipping.")
                skipped += 1
                continue

            # Upload primary image(s) for the article
            article_success = False
            for img_idx, img_path in enumerate(img_files):
                if stop_event and stop_event.is_set():
                    cancelled = True
                    break

                is_first = (img_idx == 0)
                mime_type = mimetypes.guess_type(img_path.name)[0] or "image/jpeg"

                try:
                    with open(img_path, "rb") as f_img:
                        files = {
                            "image": (img_path.name, f_img, mime_type)
                        }
                        payload = {
                            "space_name": cat_name,
                            "category_name": sub_name,
                            "reference": title,
                            "description": title,
                            "tags": f"{cat_name}, {sub_name}",
                            "is_default": "true" if is_first else "false",
                        }

                        resp = requests.post(
                            upload_endpoint,
                            files=files,
                            data=payload,
                            auth=auth,
                            timeout=45,
                        )

                    if resp.status_code == 201:
                        _log(f"  ✓ Uploaded image '{img_path.name}' successfully.")
                        article_success = True
                    elif resp.status_code == 400 and ("already exists" in resp.text.lower() or "identical image" in resp.text.lower()):
                        _log(f"  ℹ️ Image '{img_path.name}' already exists on server (duplicate skipped).")
                        article_success = True
                    elif resp.status_code in (401, 403):
                        _log(f"  ✗ Authentication denied (HTTP {resp.status_code}): {resp.text[:120]}")
                        failed += 1
                        # Break whole process if unauthorized
                        cancelled = True
                        break
                    else:
                        _log(f"  ✗ Server rejected '{img_path.name}' (HTTP {resp.status_code}): {resp.text[:140]}")
                except Exception as exc:
                    _log(f"  ✗ Network error uploading '{img_path.name}': {exc}")

            if cancelled:
                break

            if article_success:
                succeeded += 1
            else:
                failed += 1

        final_pct = 100.0 if not cancelled else ((succeeded + failed) / max(total_targeted, 1)) * 100.0
        if progress_cb:
            try:
                status_txt = "Upload finished" if not cancelled else "Upload stopped"
                progress_cb(min(idx + 1, total_targeted), total_targeted, "Complete", status_txt, final_pct)
            except RuntimeError:
                pass

        _log(f"\n=== Upload Summary: {succeeded}/{total_targeted} succeeded, {failed} failed, {skipped} skipped ===")
        return {
            "total": total_targeted,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "cancelled": cancelled,
        }


# Singleton instance
upload_manager = UploadManager()
