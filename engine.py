import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any
import requests

from browser_manager import BrowserManager
from config import (
    CATEGORIES_FILE,
    SELECTED_FEEDS_FILE,
    FEEDS_DIR,
    USER_AGENT,
    HEADLESS,
)
from scraper import Scraper
from utils import (
    get_feed,
    extract_download_url,
    download_from_locker,
    resolve_gdrive_from_locker,
    _download_from_gdrive,
)

logger = logging.getLogger("engine")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" .")


def load_categories(force_refresh: bool = False) -> List[Dict]:
    """Loads categories from JSON cache, or scrapes site if missing or force_refresh is True."""
    cat_path = Path(CATEGORIES_FILE)
    if not force_refresh and cat_path.exists():
        try:
            with open(cat_path, encoding="utf-8") as f:
                cats = json.load(f)
                if cats:
                    logger.info("Loaded %d categories from cache (%s)", len(cats), cat_path)
                    return cats
        except Exception as e:
            logger.warning("Failed loading categories cache: %s", e)

    logger.info("Scraping categories from site...")
    scraper = Scraper()
    cats = scraper.get_categories()
    if cats:
        cat_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump(cats, f, ensure_ascii=False, indent=4)
        logger.info("Saved %d categories to %s", len(cats), cat_path)
    return cats


def load_cache() -> Dict[str, Dict]:
    sel_path = Path(SELECTED_FEEDS_FILE)
    if not sel_path.exists():
        return {}
    try:
        with open(sel_path, encoding="utf-8") as f:
            data = json.load(f)
        cache = {}
        for group in data.get("selected", []):
            for entry in group.get("feed_entries", []):
                link = entry.get("link")
                if link:
                    cache[link] = entry
        logger.info("Loaded %d cached entries from %s", len(cache), sel_path)
        return cache
    except Exception as e:
        logger.warning("Failed to load cache: %s", e)
        return {}


def save_cache(all_data: List[Dict]):
    sel_path = Path(SELECTED_FEEDS_FILE)
    sel_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "selected": all_data,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(sel_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    logger.info("Saved scrape session cache to %s", sel_path)


def download_images(page, entry: Dict, folder: Path, log_cb: Optional[Callable] = None) -> Tuple[List[str], Optional[str]]:
    link = entry["link"]
    title = entry["title"]
    safe_title = sanitize(title)[:80].rstrip(" .")
    dest = folder / safe_title
    dest.mkdir(parents=True, exist_ok=True)

    cached = entry.get("downloaded_images", [])
    if cached and all(os.path.exists(p) for p in cached):
        if log_cb:
            log_cb(f"  All {len(cached)} images cached for '{safe_title[:35]}'")
        return cached, entry.get("download_url")

    if log_cb:
        log_cb(f"  Fetching article for images: {link}")

    try:
        page.goto(link, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
    except Exception as e:
        if log_cb:
            log_cb(f"  Failed loading article page: {e}")
        return cached, entry.get("download_url")

    entry_div = page.query_selector(".entry-content")
    imgs = entry_div.query_selector_all("img") if entry_div else page.query_selector_all(".post-content img, article img, .single-content img")

    downloaded = [p for p in cached if os.path.exists(p)]
    for img in imgs:
        src = img.get_attribute("src") or img.get_attribute("data-src") or ""
        if not src or "wp-content/uploads" not in src:
            continue
        src = src.split("?")[0]
        if src.endswith(".gif") or "logo" in src or "banner" in src or "icon" in src:
            continue
        ext = Path(src.split("?")[0]).suffix or ".jpg"
        name = f"image_{len(downloaded) + 1}{ext}"
        img_path = dest / name
        if img_path.exists() and img_path.stat().st_size > 0:
            if str(img_path) not in downloaded:
                downloaded.append(str(img_path))
            continue
        try:
            resp = session.get(src, timeout=15)
            resp.raise_for_status()
            with open(img_path, "wb") as f:
                f.write(resp.content)
            downloaded.append(str(img_path))
            if log_cb:
                log_cb(f"    Saved image: {name}")
        except Exception as e:
            logger.debug("Failed saving image %s: %s", src, e)

    download_url = entry.get("download_url")
    if not download_url:
        code_el = page.query_selector("div[data-locker-id] code")
        if code_el:
            text = code_el.text_content() or ""
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("http"):
                    download_url = line
                    break

    if log_cb:
        log_cb(f"  Downloaded {len(downloaded)} images for '{safe_title[:35]}'")
    return downloaded, download_url


def resolve_and_download_single_article(
    article_url: str,
    download_model: bool = True,
    download_imgs: bool = True,
    dest_dir: Optional[Path] = None,
    log_cb: Optional[Callable] = None,
    progress_cb: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Given any sketchup.cgtips.org article URL, resolves content locker, extracts GDrive link,
    and downloads model file and images.
    """
    def _log(msg: str):
        if log_cb:
            log_cb(msg)
        logger.info(msg)

    _log(f"Starting direct resolver for: {article_url}")
    dest_dir = dest_dir or FEEDS_DIR / "Direct_Downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)

    bm = BrowserManager(headless=HEADLESS)
    p_ctx, context = bm.get_context()
    page = context.new_page()

    result = {
        "article_url": article_url,
        "title": "",
        "locker_url": "",
        "gdrive_url": "",
        "model_file": None,
        "images": [],
        "success": False,
        "error": None,
    }

    try:
        # 1. Load article page
        _log("Fetching article page...")
        page.goto(article_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        title_el = page.query_selector("h1.entry-title, h1")
        title = title_el.text_content().strip() if title_el else "article"
        result["title"] = title
        safe_title = sanitize(title)[:80].rstrip(" .")
        article_folder = dest_dir / safe_title
        article_folder.mkdir(parents=True, exist_ok=True)
        _log(f"Article title: '{title}'")

        # 2. Extract locker URL
        locker_url = None
        code_el = page.query_selector("div[data-locker-id] code")
        if code_el:
            text = code_el.text_content() or ""
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("http"):
                    locker_url = line
                    break

        if not locker_url:
            locker_url = extract_download_url(article_url)

        result["locker_url"] = locker_url
        if locker_url:
            _log(f"Found content locker URL: {locker_url}")
        else:
            _log("No content locker found on article page")

        # 3. Download images if requested
        if download_imgs:
            _log("Extracting and downloading images...")
            entry = {"link": article_url, "title": title, "download_url": locker_url}
            imgs, updated_url = download_images(page, entry, dest_dir, log_cb=log_cb)
            result["images"] = imgs
            if updated_url and not locker_url:
                locker_url = updated_url
                result["locker_url"] = locker_url

        # 4. Download model if requested and locker found
        if download_model and locker_url:
            _log(f"Resolving locker countdown and Google Drive link...")
            model_folder = article_folder / "model"
            model_folder.mkdir(parents=True, exist_ok=True)

            gdrive_url = resolve_gdrive_from_locker(page, locker_url)
            result["gdrive_url"] = gdrive_url
            if gdrive_url:
                _log(f"Extracted Google Drive URL: {gdrive_url}")
                _log("Downloading model archive...")
                model_file = _download_from_gdrive(page, gdrive_url, model_folder, progress_cb=progress_cb)
                result["model_file"] = model_file
                if model_file:
                    _log(f"Model saved: {Path(model_file).name} ({os.path.getsize(model_file)} bytes)")
                    result["success"] = True
                else:
                    _log("Model download failed (quota or file unreachable)")
            else:
                _log("Could not find Google Drive link on locker page")
        elif not download_model:
            result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        _log(f"Resolver error: {e}")
    finally:
        try:
            context.close()
            p_ctx.stop()
        except Exception:
            pass

    return result
