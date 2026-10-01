"""
CGTips Scraper Direct Service
Provides in-process, direct execution of the scraper engine without requiring
a separate FastAPI server or REST API layer.
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QUrl

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    BASE_DIR,
    FEEDS_DIR,
    CATEGORIES_FILE,
    SELECTED_FEEDS_FILE,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    USER_AGENT,
    HEADLESS,
)
from engine import load_categories, resolve_and_download_single_article
from utils import get_feed
from .library import library_manager, format_bytes
from gdrive_api import check_gdrive_status
from desktop.backend.image_provider import image_provider_instance

logger = logging.getLogger("scraper_service")


class ScraperService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def search(self, query: str, page: int = 1) -> List[Dict[str, Any]]:
        """Directly searches CGTips for SketchUp 3D models."""
        q = query.strip()
        if not q:
            return []

        url = f"https://sketchup.cgtips.org/?s={requests.utils.quote(q)}"
        if page > 1:
            url = f"https://sketchup.cgtips.org/page/{page}/?s={requests.utils.quote(q)}"

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for art in soup.select("article"):
            title_el = art.select_one(".entry-title a, h2 a, h1 a")
            if not title_el:
                continue
            title = title_el.text.strip()
            link = title_el.get("href", "")

            # High-res thumbnail extraction from responsive srcset or img
            thumb = None
            img_holder = art.select_one(".img-holder")
            if img_holder and img_holder.get("data-bs-srcset"):
                try:
                    srcset = json.loads(img_holder["data-bs-srcset"])
                    base = srcset.get("baseurl", "")
                    sizes = srcset.get("sizes", {})
                    best_size = (
                        sizes.get("750")
                        or sizes.get("357")
                        or sizes.get("210")
                        or (list(sizes.values())[0] if sizes else "")
                    )
                    if base and best_size:
                        thumb = base + best_size
                except Exception:
                    pass

            if not thumb:
                img = art.select_one("img")
                if img:
                    thumb = img.get("src") or img.get("data-src")

            cat_el = art.select_one(".term-badge a, .category a")
            category = cat_el.text.strip() if cat_el else ""

            thumb_url = thumb or ""
            thumb_display = f"image://cgtips/{requests.utils.quote(thumb_url, safe='')}" if thumb_url.startswith("http") else thumb_url

            results.append({
                "title": title,
                "link": link,
                "thumbnail": thumb_display,
                "thumbnail_full": thumb_display,
                "raw_thumbnail": thumb_url,
                "category": category,
            })

        thumbs_to_fetch = [r["raw_thumbnail"] for r in results if r.get("raw_thumbnail")]
        if thumbs_to_fetch:
            image_provider_instance.prefetch(thumbs_to_fetch)

        return results

    def get_categories(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Loads categories hierarchy from cache or directly scrapes site."""
        raw_cats = load_categories(force_refresh=refresh)
        normalized = []
        for cat in raw_cats:
            heading = cat.get("heading") or {}
            cat_name = cat.get("name") or heading.get("name") or cat.get("title") or "Category"
            cat_url = cat.get("url") or heading.get("url") or ""
            cat_feed = cat.get("feed_url") or heading.get("feed_url") or ""
            subs = []
            for sub in cat.get("subcategories", []):
                sub_name = sub.get("name") or sub.get("title") or "Subcategory"
                subs.append({
                    "name": sub_name,
                    "title": sub_name,
                    "url": sub.get("url", ""),
                    "feed_url": sub.get("feed_url", ""),
                })
            normalized.append({
                "name": cat_name,
                "title": cat_name,
                "url": cat_url,
                "feed_url": cat_feed,
                "subcategories": subs,
            })
        return normalized

    def get_feed_preview(self, feed_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetches RSS feed entries directly."""
        clean_url = feed_url.strip()
        if not clean_url:
            return []
        entries = get_feed(feed_url=clean_url, max_items=limit)
        items = []
        for e in entries:
            raw_img = e.get("image_url", "")
            img_display = f"image://cgtips/{requests.utils.quote(raw_img, safe='')}" if raw_img.startswith("http") else raw_img
            items.append({
                "title": e.get("title", "Untitled Article"),
                "link": e.get("link", ""),
                "published": e.get("pub_date", "") or e.get("published", ""),
                "image_url": img_display,
                "raw_image_url": raw_img,
                "creator": e.get("creator", ""),
                "download_url": e.get("download_url", ""),
            })

        imgs_to_fetch = [item["raw_image_url"] for item in items if item.get("raw_image_url")]
        if imgs_to_fetch:
            image_provider_instance.prefetch(imgs_to_fetch)

        return items


    def resolve_article(
        self,
        article_url: str,
        download_model: bool = True,
        download_images: bool = True,
        log_cb: Optional[Callable[[str], None]] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Resolves content lockers and downloads model + images directly."""
        dest_folder = FEEDS_DIR / "Direct_Downloads"
        dest_folder.mkdir(parents=True, exist_ok=True)

        res = resolve_and_download_single_article(
            article_url=article_url.strip(),
            download_model=download_model,
            download_imgs=download_images,
            dest_dir=dest_folder,
            log_cb=log_cb,
            progress_cb=progress_cb,
        )

        # Convert local image paths to file:// QUrl strings
        imgs = res.get("images", [])
        imgs_file_urls = []
        for img_path in imgs:
            p = Path(img_path).resolve()
            if p.exists():
                imgs_file_urls.append(QUrl.fromLocalFile(str(p)).toString())

        res["images_full"] = imgs_file_urls
        res["first_image"] = imgs_file_urls[0] if imgs_file_urls else ""
        return res

    def get_library(self, search: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Scans local media library and formats image file:// URLs."""
        cat_filter = category if (category and category != "all") else None
        data = library_manager.scan_library(search=search or None, category_filter=cat_filter)

        items = data.get("items", [])
        for item in items:
            raw_imgs = item.get("images", [])
            imgs_file_urls = []
            for rel_img in raw_imgs:
                p = (FEEDS_DIR / rel_img).resolve()
                if p.exists():
                    imgs_file_urls.append(QUrl.fromLocalFile(str(p)).toString())

            item["images_full"] = imgs_file_urls
            item["first_image"] = imgs_file_urls[0] if imgs_file_urls else ""

            # Local folder and model path
            full_folder = (FEEDS_DIR / item["folder_path"]).resolve()
            item["folder_full_path"] = str(full_folder)

            if item.get("model_path"):
                full_model = (FEEDS_DIR / item["model_path"]).resolve()
                item["model_file_full"] = str(full_model)
            else:
                item["model_file_full"] = ""

        return {
            "total": len(items),
            "items": items,
            "stats": data.get("stats", {}),
            "categories": data.get("categories", []),
        }

    def delete_model(self, folder_path: str) -> bool:
        """Deletes a local model directory from the filesystem."""
        return library_manager.delete_item(folder_path)

    def retry_model(self, folder_path: str, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Finds article URL and re-runs model extraction directly."""
        article_dir = (FEEDS_DIR / folder_path).resolve()
        if not article_dir.exists():
            if log_cb:
                log_cb(f"Folder not found: {folder_path}")
            return False

        meta = library_manager.get_meta(article_dir)
        article_url = meta.get("article_url")

        if not article_url:
            if log_cb:
                log_cb("Looking up article URL on CGTips...")
            article_url = library_manager.find_article_url_on_site(article_dir)

        if not article_url:
            if log_cb:
                log_cb("Could not find article URL for this item")
            return False

        if log_cb:
            log_cb(f"Re-downloading model from: {article_url}")

        result = resolve_and_download_single_article(
            article_url=article_url,
            dest_dir=article_dir.parent,
            download_model=True,
            download_imgs=False,
            log_cb=log_cb,
        )
        return bool(result.get("success") and result.get("model_file"))

    def get_system_status(self) -> Dict[str, Any]:
        """Returns direct scraper status and disk metrics."""
        lib = library_manager.scan_library()
        gdrive = check_gdrive_status()

        return {
            "mode": "Direct Scraper Engine (In-Process)",
            "feeds_dir": str(FEEDS_DIR),
            "library_summary": lib.get("stats", {}),
            "gdrive": gdrive,
            "categories_cached": Path(CATEGORIES_FILE).exists(),
            "selected_feeds_cached": Path(SELECTED_FEEDS_FILE).exists(),
            "headless": HEADLESS,
            "user_agent": USER_AGENT,
        }

    def clear_cache(self, target: str = "categories") -> List[str]:
        """Clears specified cache files."""
        cleared = []
        if target in ("categories", "all"):
            p = Path(CATEGORIES_FILE)
            if p.exists():
                p.unlink()
                cleared.append("categories.json")

        if target in ("history", "all"):
            p = Path(SELECTED_FEEDS_FILE)
            if p.exists():
                p.unlink()
                cleared.append("selected_feeds.json")

        if target == "all":
            p = Path(TOKEN_FILE)
            if p.exists():
                p.unlink()
                cleared.append("token.pickle")

        return cleared


# Singleton service instance
scraper_service = ScraperService()
