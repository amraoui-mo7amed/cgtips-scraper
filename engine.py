import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any
import requests

import config
from browser_manager import BrowserManager
from config import (
    CATEGORIES_FILE,
    SELECTED_FEEDS_FILE,
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


def write_meta(article_dir: Path, **fields) -> None:
    """Merges fields into <article_dir>/meta.json (used by the Library)."""
    if not Path(article_dir).is_dir():
        return
    meta_file = Path(article_dir) / "meta.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    meta.update({k: v for k, v in fields.items() if v not in (None, "")})
    try:
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to write meta %s: %s", meta_file, e)


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
    page=None,
    title_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Given any sketchup.cgtips.org article URL, resolves content locker, extracts GDrive link,
    and downloads model file and images.

    If `page` is given it is reused (and left open) instead of launching a new browser,
    which is what the bulk downloader does. `title_hint` fixes the article folder name
    so it is predictable (and can be checked before downloading).
    """
    def _log(msg: str):
        if log_cb:
            log_cb(msg)
        logger.info(msg)

    _log(f"Starting direct resolver for: {article_url}")
    dest_dir = dest_dir or config.FEEDS_DIR / "Direct_Downloads" / "Direct"
    dest_dir.mkdir(parents=True, exist_ok=True)

    owns_browser = page is None
    p_ctx = context = None
    if owns_browser:
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
        title = (title_hint or "").strip() or (title_el.text_content().strip() if title_el else "article")
        result["title"] = title
        safe_title = sanitize(title)[:80].rstrip(" .")
        article_folder = dest_dir / safe_title
        article_folder.mkdir(parents=True, exist_ok=True)
        _log(f"Article title: '{title}'")
        write_meta(article_folder, article_url=article_url, title=title)

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
        if owns_browser:
            try:
                context.close()
                p_ctx.stop()
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# Bulk download
# ---------------------------------------------------------------------------

def article_folder_for(category: str, subcategory: str, title: str) -> Path:
    """Where a bulk-downloaded article lives: <feeds>/<category>/<subcategory>/<title>."""
    safe_title = sanitize(title)[:80].rstrip(" .")
    return config.FEEDS_DIR / (sanitize(category) or "Imported") / (sanitize(subcategory) or "Imported") / safe_title


def _article_complete(folder: Path, need_model: bool, need_images: bool) -> bool:
    """True if everything requested for this article is already on disk."""
    if not folder.is_dir():
        return False
    if need_model:
        model_dir = folder / "model"
        if not (model_dir.is_dir() and any(
            f.is_file() and not f.name.startswith(".") and f.stat().st_size > 0 for f in model_dir.iterdir()
        )):
            return False
    if need_images:
        if not any(f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") for f in folder.iterdir() if f.is_file()):
            return False
    return True


def bulk_download(
    groups: List[Dict[str, Any]],
    download_model: bool = True,
    download_imgs: bool = True,
    max_items: int = 0,
    skip_existing: bool = True,
    state_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """
    Downloads many articles with a single shared browser.

    Each group is {"category", "subcategory"} plus either "articles"
    (a list of {"title", "link"}) or "feed_url" (the sub-category feed is
    fetched, up to `max_items` entries, 0 = all). Articles already in the
    library are skipped, so an interrupted run can simply be started again.
    """
    cancel_event = cancel_event or threading.Event()
    state: Dict[str, Any] = {
        "running": True, "phase": "listing", "total": 0, "done": 0,
        "succeeded": 0, "skipped": 0, "failed": 0, "current": "",
        "cancelled": False, "failures": [],
    }

    def _emit():
        if state_cb:
            state_cb(dict(state, failures=list(state["failures"])))

    def _log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    _emit()

    # 1. Build the work list (fetching feeds for sub-category groups).
    work: List[Dict[str, str]] = []
    seen = set()
    for g in groups:
        if cancel_event.is_set():
            break
        category, sub = g.get("category") or "", g.get("subcategory") or ""
        articles = g.get("articles")
        if articles is None:
            feed_url = g.get("feed_url") or ""
            state["current"] = f"Listing {category} › {sub}"
            _emit()
            try:
                articles = get_feed(feed_url=feed_url, max_items=max_items) if feed_url else []
            except Exception as e:
                _log(f"Could not read feed for {sub}: {e}")
                articles = []
            _log(f"{category} › {sub}: {len(articles)} articles")
        for a in articles:
            link = (a.get("link") or "").strip()
            if not link or link in seen:
                continue
            seen.add(link)
            work.append({"title": a.get("title") or "", "link": link, "category": category, "subcategory": sub})

    state.update(total=len(work), phase="downloading", current="")
    _emit()

    # 2. Download, one article at a time, reusing a single browser page.
    bm = p_ctx = context = page = None

    def _open_browser():
        nonlocal bm, p_ctx, context, page
        bm = BrowserManager(headless=HEADLESS)
        p_ctx, context = bm.get_context()
        page = context.new_page()

    def _close_browser():
        nonlocal p_ctx, context, page
        try:
            if context:
                context.close()
            if p_ctx:
                p_ctx.stop()
        except Exception:
            pass
        p_ctx = context = page = None

    try:
        for item in work:
            if cancel_event.is_set():
                state["cancelled"] = True
                break
            label = item["title"] or item["link"]
            state["current"] = label
            _emit()

            folder = article_folder_for(item["category"], item["subcategory"], item["title"]) if item["title"] else None
            if skip_existing and folder and _article_complete(folder, download_model, download_imgs):
                state["skipped"] += 1
                state["done"] += 1
                _log(f"Skipped (already downloaded): {label[:70]}")
                _emit()
                continue

            try:
                if page is None:
                    _open_browser()
                dest = config.FEEDS_DIR / (sanitize(item["category"]) or "Imported") / (sanitize(item["subcategory"]) or "Imported")
                state.update(bytes_done=0, bytes_total=0)
                last_emit = [0.0]

                def _bytes(done: int, total: int, _name: str = ""):
                    state.update(bytes_done=done, bytes_total=total)
                    if time.monotonic() - last_emit[0] > 0.4 or (total and done >= total):
                        last_emit[0] = time.monotonic()
                        _emit()

                res = resolve_and_download_single_article(
                    item["link"],
                    download_model=download_model,
                    download_imgs=download_imgs,
                    dest_dir=dest,
                    log_cb=log_cb,
                    progress_cb=_bytes,
                    page=page,
                    title_hint=item["title"],
                )
                ok = bool(res.get("success")) or (not download_model and bool(res.get("images")))
                if res.get("title"):
                    write_meta(
                        dest / sanitize(res["title"])[:80].rstrip(" ."),
                        article_url=item["link"], category=item["category"], subcategory=item["subcategory"],
                    )
            except Exception as e:
                ok = False
                res = {"error": str(e)}
                _log(f"Error on {label[:60]}: {e}")
                _close_browser()  # next article starts from a fresh browser

            if not ok and page is not None:
                # A failed goto can leave a navigation pending on the page, which then
                # interrupts every following article; give the next one a clean tab.
                try:
                    page.close()
                    page = context.new_page()
                except Exception:
                    _close_browser()

            if ok:
                state["succeeded"] += 1
            else:
                state["failed"] += 1
                state["failures"].append({"title": label, "link": item["link"], "error": res.get("error") or "Download failed"})
            state["done"] += 1
            _emit()
    finally:
        _close_browser()
        state.update(running=False, phase="cancelled" if state["cancelled"] else "finished", current="")
        _emit()

    return state
