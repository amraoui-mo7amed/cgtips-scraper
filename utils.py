import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, Callable
import cloudscraper
import requests
from bs4 import BeautifulSoup as bs
from decouple import config
from tqdm import tqdm

from config import USER_AGENT

logger = logging.getLogger("utils")

FEED_UA = USER_AGENT

sess = cloudscraper.create_scraper()
sess.headers.update({
    "User-Agent": FEED_UA,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://sketchup.cgtips.org/",
    "DNT": "1",
})


def get_feed(feed_url=None, max_items=0, page=None):
    if feed_url is None:
        feed_url = "https://sketchup.cgtips.org/tag/tea-room/feed/"

    base = feed_url.rstrip("/")
    page_pattern = base.replace("/feed", "/feed/?paged={}") if base.endswith("/feed") else base + "?paged={}"

    all_entries = []
    for pg in range(1, 51):
        url = page_pattern.format(pg) if pg > 1 else feed_url
        resp = None
        for attempt in range(3):
            try:
                resp = sess.get(url, timeout=30)
                resp.raise_for_status()
                break
            except Exception:
                if attempt == 2:
                    break
                time.sleep(2 ** attempt)
        if resp is None:
            break

        try:
            soup = bs(resp.content, "xml")
        except Exception:
            soup = bs(resp.content, "html.parser")
        items = soup.find_all("item")
        if not items:
            break

        for item in items:
            title = (item.find("title").text.strip()) if item.find("title") else ""
            link = (item.find("link").text.strip()) if item.find("link") else ""
            desc = (item.find("description").text.strip()) if item.find("description") else ""
            img_match = re.search(r'<img[^>]+src="([^"]+)"', desc)
            all_entries.append({
                "title": title,
                "link": link,
                "pub_date": (item.find("pubDate").text.strip()) if item.find("pubDate") else "",
                "creator": (item.find("dc:creator").text.strip()) if item.find("dc:creator") else "",
                "categories": [cat.text.strip() for cat in item.find_all("category")],
                "image_url": img_match.group(1) if img_match else "",
            })

        if max_items > 0 and len(all_entries) >= max_items:
            all_entries = all_entries[:max_items]
            break

        time.sleep(0.3)

    if not all_entries and page is not None:
        logger.info("cloudscraper returned nothing, falling back to Playwright")
        all_entries = _get_feed_playwright(feed_url, max_items, page)

    return all_entries


def _get_feed_playwright(feed_url, max_items, page):
    base = feed_url.rstrip("/")
    page_pattern = base.replace("/feed", "/feed/?paged={}") if base.endswith("/feed") else base + "?paged={}"

    all_entries = []
    for pg in range(1, 51):
        url = page_pattern.format(pg) if pg > 1 else feed_url
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = page.content()
        except Exception:
            break

        soup = bs(content, "xml")
        items = soup.find_all("item")
        if not items:
            break

        for item in items:
            title = (item.find("title").text.strip()) if item.find("title") else ""
            link = (item.find("link").text.strip()) if item.find("link") else ""
            desc = (item.find("description").text.strip()) if item.find("description") else ""
            img_match = re.search(r'<img[^>]+src="([^"]+)"', desc)
            all_entries.append({
                "title": title,
                "link": link,
                "pub_date": (item.find("pubDate").text.strip()) if item.find("pubDate") else "",
                "creator": (item.find("dc:creator").text.strip()) if item.find("dc:creator") else "",
                "categories": [cat.text.strip() for cat in item.find_all("category")],
                "image_url": img_match.group(1) if img_match else "",
            })

        if max_items > 0 and len(all_entries) >= max_items:
            all_entries = all_entries[:max_items]
            break

        time.sleep(0.3)

    return all_entries


def extract_download_url(article_url, retries=3):
    """Fetches article page and finds locker link inside data-locker-id code."""
    for attempt in range(1, retries + 1):
        try:
            resp = sess.get(article_url, timeout=30)
            resp.raise_for_status()
            soup = bs(resp.content, "html.parser")
            code_el = soup.select_one("div[data-locker-id] code")
            if code_el:
                text = code_el.get_text() or ""
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("http"):
                        return line
            return None
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
    return None


def resolve_gdrive_from_locker(page, locker_url):
    """Loads content locker page with Playwright and extracts Google Drive destination URL."""
    try:
        page.goto(locker_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        gdrive_url = page.evaluate("""() => {
            const btn = document.querySelector('.download_dem a.btn');
            if (btn && btn.href) return btn.href;
            const anyLink = Array.from(document.querySelectorAll('a')).find(a => a.href && a.href.includes('drive.google.com'));
            return anyLink ? anyLink.href : null;
        }""")
        return gdrive_url
    except Exception as e:
        logger.warning("Failed to resolve locker %s: %s", locker_url, e)
        return None


def download_from_locker(page, locker_url, dest_path, progress_cb: Optional[Callable] = None):
    try:
        gdrive_url = resolve_gdrive_from_locker(page, locker_url)
        if not gdrive_url or "drive.google.com" not in gdrive_url:
            logger.warning("No valid Google Drive URL extracted from %s", locker_url)
            return None

        return _download_from_gdrive(page, gdrive_url, dest_path, progress_cb=progress_cb)
    except Exception as e:
        logger.error("Error downloading from locker %s: %s", locker_url, e)
        return None


def _download_req(file_id, dest_path, progress_cb: Optional[Callable] = None):
    s = cloudscraper.create_scraper()
    s.headers.update({"User-Agent": FEED_UA})
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    r = s.get(url, allow_redirects=False, timeout=30)
    r.raise_for_status()

    if r.status_code == 303:
        r = s.get(r.headers["Location"], timeout=30)
        r.raise_for_status()

    ct = r.headers.get("Content-Type", "")

    if "text/html" in ct and int(r.headers.get("Content-Length", 0)) < 10000:
        if "Virus scan warning" in r.text:
            soup = bs(r.content, "html.parser")
            form = soup.find("form")
            if not form:
                return None
            action = form.get("action")
            data = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
            r = s.get(action, params=data, stream=True, timeout=60)
            r.raise_for_status()

        if b"Quota exceeded" in r.content or b"Too many users" in r.content:
            logger.warning("Direct GDrive download hit quota limit for %s", file_id)
            return None

        ct = r.headers.get("Content-Type", "")

    cd = r.headers.get("Content-Disposition")
    name = None
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
        if m:
            from urllib.parse import unquote
            name = unquote(m.group(1))
    if not name:
        name = f"{file_id}.zip"

    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .") or f"{file_id}.zip"
    path = dest_path / name
    total = int(r.headers.get("Content-Length", 0))
    downloaded = 0

    # Write to a hidden temp file and only rename once complete, so an interrupted
    # download (disk full, network drop) never shows up as a finished model.
    part = dest_path / f".{name}.part"
    try:
        with open(part, "wb") as f:
            with tqdm(total=total, unit='B', unit_scale=True, desc=name[:35], leave=False) as pbar:
                for chunk in r.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        pbar.update(len(chunk))
                        if progress_cb:
                            progress_cb(downloaded, total, name)
        if total and downloaded < total:
            raise IOError(f"Download incomplete: {downloaded} of {total} bytes")
        os.replace(part, path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    return str(path)


def _download_pw(page, file_id, dest_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    for attempt in range(2):
        try:
            if attempt == 0:
                with page.expect_download(timeout=15000) as info:
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                dl = info.value
            else:
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                if "Quota" in page.content()[:5000]:
                    return None
                btn = page.query_selector("input[type='submit'], form a[href*='confirm'], a:has-text('Download')")
                if not btn:
                    return None
                with page.expect_download(timeout=30000) as info:
                    btn.click()
                dl = info.value

            p = dest_path / dl.suggested_filename
            dl.save_as(str(p))
            if p.stat().st_size > 0:
                return str(p)
        except Exception:
            continue
    return None


def _download_from_gdrive(page, gdrive_url, dest_path, progress_cb: Optional[Callable] = None):
    m = re.search(r"/file/d/([^/]+)", gdrive_url)
    if not m:
        return None
    file_id = m.group(1)
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    # 1. Direct requests download (fastest)
    result = _download_req(file_id, dest_path, progress_cb=progress_cb)
    if result:
        return result

    # 2. GDrive API quota bypass
    try:
        from gdrive_api import copy_and_download
        logger.info("Direct download failed/quota limited, attempting Drive API bypass for %s", file_id)
        result = copy_and_download(file_id, dest_path)
        if result:
            return result
    except Exception as e:
        logger.debug("Drive API fallback bypassed: %s", e)

    # 3. Playwright browser download fallback
    if page:
        logger.info("Attempting browser download fallback for %s", file_id)
        result = _download_pw(page, file_id, dest_path)
        return result

    return None
