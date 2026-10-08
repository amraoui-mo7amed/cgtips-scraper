import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
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
    """Loads content locker page with Playwright and extracts Google Drive or mirror destination URL."""
    try:
        page.goto(locker_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        # Check for immediate link
        dl_url = page.evaluate("""() => {
            const btn = document.querySelector('.download_dem a.btn, a.btn-download, a#download-btn');
            if (btn && btn.href && btn.href.startsWith('http')) return btn.href;
            const mirrors = ['drive.google.com', 'mediafire.com', 'mega.nz', 'dropbox.com'];
            for (const a of document.querySelectorAll('a')) {
                if (a.href && mirrors.some(m => a.href.includes(m))) {
                    return a.href;
                }
            }
            return null;
        }""")

        # If not ready (countdown timer running), wait a bit and recheck
        if not dl_url:
            page.wait_for_timeout(4500)
            dl_url = page.evaluate("""() => {
                const btn = document.querySelector('.download_dem a.btn, a.btn-download');
                if (btn && btn.href && btn.href.startsWith('http')) return btn.href;
                const anyDrive = Array.from(document.querySelectorAll('a')).map(a => a.href).find(h => h && h.includes('drive.google.com'));
                return anyDrive || null;
            }""")

        return dl_url
    except Exception as e:
        logger.warning("Failed to resolve locker %s: %s", locker_url, e)
        return None


def download_from_locker(
    page,
    locker_url,
    dest_path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    try:
        dl_url = resolve_gdrive_from_locker(page, locker_url)
        if not dl_url:
            logger.warning("No valid download URL extracted from %s", locker_url)
            return None

        return _download_from_gdrive(
            page,
            dl_url,
            dest_path,
            progress_cb=progress_cb,
            log_cb=log_cb,
            cancel_event=cancel_event,
        )
    except Exception as e:
        logger.error("Error downloading from locker %s: %s", locker_url, e)
        return None


class DownloadPaused(Exception):
    """Raised when a model download is paused. The partial file is kept so it can resume."""

    def __init__(self, msg: str = "Paused"):
        super().__init__(msg)
        self.gdrive_url = ""
        self.folder = ""


def _parse_total(r, offset: int) -> int:
    """Full file size from a 200 or 206 response (0 when unknown)."""
    if r.status_code == 206:
        m = re.search(r"/(\d+)\s*$", r.headers.get("Content-Range", ""))
        if m:
            return int(m.group(1))
        return offset + int(r.headers.get("Content-Length", 0) or 0)
    return int(r.headers.get("Content-Length", 0) or 0)


def _stream_response_to_file(
    r,
    dest_path: Path,
    fallback_name: str,
    progress_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
    offset: int = 0,
    parts: Optional[List[Path]] = None,
) -> Optional[str]:
    """Streams an HTTP response to a temporary part file and moves it to the final destination."""
    parts = parts or []
    cd = r.headers.get("Content-Disposition")
    name = None
    if cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
        if m:
            from urllib.parse import unquote
            name = unquote(m.group(1))
    if not name:
        name = fallback_name

    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .") or fallback_name
    path = dest_path / name

    part = dest_path / f".{name}.part"
    resuming = r.status_code == 206 and part.exists() and part.stat().st_size == offset
    for stale in parts:
        if stale != part or not resuming:
            stale.unlink(missing_ok=True)
    downloaded = offset if resuming else 0
    total = _parse_total(r, offset) if resuming else int(r.headers.get("Content-Length", 0) or 0)

    try:
        with open(part, "ab" if resuming else "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if cancel_event is not None and cancel_event.is_set():
                    raise DownloadPaused()
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total, name)
        if total and downloaded < total:
            raise IOError(f"Download incomplete: {downloaded} of {total} bytes")
        os.replace(part, path)
    except DownloadPaused:
        r.close()
        raise
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    return str(path)


def _download_req(
    file_id: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 1: Direct requests stream across multiple Google Drive endpoints."""
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    parts = sorted(dest_path.glob(".*.part"))
    offset = parts[0].stat().st_size if parts else 0
    range_hdr = {"Range": f"bytes={offset}-"} if offset else {}

    candidate_urls = [
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&id={file_id}",
        f"https://docs.google.com/uc?export=download&id={file_id}",
    ]

    for candidate_url in candidate_urls:
        if cancel_event and cancel_event.is_set():
            raise DownloadPaused()
        try:
            s = cloudscraper.create_scraper()
            s.headers.update({"User-Agent": FEED_UA})
            r = s.get(candidate_url, allow_redirects=True, headers=range_hdr, timeout=30, stream=True)

            if r.status_code in (200, 206):
                ct = r.headers.get("Content-Type", "")
                if "text/html" not in ct:
                    # Direct binary stream found!
                    return _stream_response_to_file(r, dest_path, f"{file_id}.zip", progress_cb, cancel_event, offset, parts)

                # HTML page returned (might be Virus Scan Warning form)
                content = r.content
                if b"Virus scan warning" in content or b"download-form" in content:
                    soup = bs(content, "html.parser")
                    form = soup.find("form")
                    if form:
                        action = form.get("action") or "https://drive.usercontent.google.com/download"
                        data = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
                        r2 = s.get(action, params=data, headers=range_hdr, stream=True, timeout=60)
                        if r2.status_code in (200, 206) and "text/html" not in r2.headers.get("Content-Type", ""):
                            return _stream_response_to_file(r2, dest_path, f"{file_id}.zip", progress_cb, cancel_event, offset, parts)

        except DownloadPaused:
            raise
        except Exception as e:
            logger.debug("Direct stream failed for URL %s: %s", candidate_url, e)

    return None


def _download_pw_full(
    page,
    file_id: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 3: Full Playwright browser automation with multi-lingual button support and popup handling."""
    if not page:
        return None
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    if log_cb:
        log_cb("  [Browser Method] Automating browser download interaction...")
    logger.info("Playwright browser download attempt for %s", file_id)

    # Attempt A: Direct uc download trigger
    try:
        url_direct = f"https://drive.google.com/uc?export=download&id={file_id}"
        with page.expect_download(timeout=10000) as info:
            page.goto(url_direct, timeout=12000, wait_until="domcontentloaded")
        dl = info.value
        name = dl.suggested_filename or f"{file_id}.zip"
        p = dest_path / name
        dl.save_as(str(p))
        if p.exists() and p.stat().st_size > 5000:
            if log_cb:
                log_cb(f"  [Browser Method] ✓ Direct browser trigger succeeded: {name}")
            return str(p)
    except Exception:
        pass

    # Attempt B: Google Drive Preview page (/file/d/.../view)
    try:
        url_view = f"https://drive.google.com/file/d/{file_id}/view"
        page.goto(url_view, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        selectors = [
            '[aria-label*="download" i]',
            '[aria-label*="télécharger" i]',
            '[aria-label*="descargar" i]',
            '[aria-label*="herunterladen" i]',
            '[aria-label*="скачать" i]',
            '[aria-label*="tải" i]',
            '[data-tooltip*="download" i]',
            '[data-tooltip*="télécharger" i]',
            '[data-tooltip*="descargar" i]',
            'div[role="button"][aria-label*="load" i]',
            'a[href*="export=download"]',
        ]
        btn = None
        for sel in selectors:
            btn = page.query_selector(sel)
            if btn:
                break

        if btn:
            popup = None
            try:
                with page.expect_popup(timeout=6000) as popup_info:
                    btn.click(force=True)
                popup = popup_info.value
            except Exception:
                pass

            target_page = popup if popup else page
            if popup:
                popup.wait_for_timeout(2000)

            sub_selectors = [
                '#uc-download-link',
                'input[type="submit"]',
                'button:has-text("Download anyway")',
                'button:has-text("Télécharger quand même")',
                'button:has-text("Descargar de todos modos")',
                'a:has-text("Download anyway")',
                'input[value*="Download" i]',
                'input[value*="Télécharger" i]',
                'form button',
            ]
            sub_btn = None
            for s_sel in sub_selectors:
                sub_btn = target_page.query_selector(s_sel)
                if sub_btn:
                    break

            if sub_btn:
                try:
                    with target_page.expect_download(timeout=20000) as dl_info:
                        sub_btn.click(force=True)
                    dl = dl_info.value
                    name = dl.suggested_filename or f"{file_id}.zip"
                    p = dest_path / name
                    dl.save_as(str(p))
                    if p.exists() and p.stat().st_size > 5000:
                        if log_cb:
                            log_cb(f"  [Browser Method] ✓ Interactive browser download succeeded: {name}")
                        return str(p)
                except Exception as dl_err:
                    logger.debug("Browser popup download click error: %s", dl_err)
    except Exception as e:
        logger.debug("Playwright browser interaction failed for %s: %s", file_id, e)

    return None


def _download_browser_cookies(
    page,
    file_id: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 4: Browser session cookie handshake with CloudScraper/requests."""
    if not page:
        return None
    try:
        cookies = page.context.cookies([
            "https://drive.google.com",
            "https://drive.usercontent.google.com",
            "https://google.com",
        ])
        if not cookies:
            return None

        if log_cb:
            log_cb("  [Cookie Handshake] Replaying browser session cookies with HTTP stream...")
        logger.info("Cookie-handshake download attempt for %s (%d cookies)", file_id, len(cookies))

        s = cloudscraper.create_scraper()
        s.headers.update({"User-Agent": USER_AGENT})
        for c in cookies:
            s.cookies.set(c["name"], c["value"], domain=c.get("domain", ".google.com"), path=c.get("path", "/"))

        url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        r = s.get(url, stream=True, timeout=60)
        ct = r.headers.get("Content-Type", "")
        if r.status_code in (200, 206) and "text/html" not in ct:
            return _stream_response_to_file(r, dest_path, f"{file_id}.zip", progress_cb, cancel_event)
    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("Cookie-session download error for %s: %s", file_id, e)
    return None


def _download_curl(
    file_id: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 5: System Curl CLI with CookieJar session."""
    if not shutil.which("curl"):
        return None
    cookie_file = dest_path / f".curl_cookie_{file_id}_{os.getpid()}.txt"
    temp_out = dest_path / f".curl_dl_{file_id}_{os.getpid()}.part"
    try:
        if log_cb:
            log_cb("  [Curl Method] Attempting system curl with cookie jar...")
        logger.info("Curl download attempt for GDrive %s", file_id)

        # Step 1: Initial request to get session cookies
        cmd1 = [
            "curl", "-s", "-L",
            "-c", str(cookie_file),
            "-A", FEED_UA,
            "--max-time", "30",
            f"https://drive.google.com/uc?export=download&id={file_id}",
        ]
        proc1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=35)
        html = proc1.stdout or ""

        target_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        uuid_m = re.search(r'name="uuid"\s+value="([^"]+)"', html)
        action_m = re.search(r'action="([^"]+)"', html)
        if uuid_m and action_m:
            target_url = f"{action_m.group(1)}?id={file_id}&export=download&confirm=t&uuid={uuid_m.group(1)}"

        # Step 2: Download with cookie jar
        cmd2 = [
            "curl", "-s", "-L",
            "-b", str(cookie_file),
            "-c", str(cookie_file),
            "-A", FEED_UA,
            "--max-time", "300",
            target_url,
            "-o", str(temp_out),
        ]
        subprocess.run(cmd2, capture_output=True, text=True, timeout=310)

        if temp_out.exists() and temp_out.stat().st_size > 10000:
            with open(temp_out, "rb") as f:
                head = f.read(512)
            if not head.startswith(b"<!DOCTYPE") and not head.startswith(b"<html"):
                final_name = f"{file_id}.zip"
                final_path = dest_path / final_name
                os.replace(temp_out, final_path)
                if log_cb:
                    log_cb(f"  [Curl Method] ✓ Successfully downloaded: {final_name}")
                return str(final_path)
    except Exception as e:
        logger.debug("Curl download failed for %s: %s", file_id, e)
    finally:
        cookie_file.unlink(missing_ok=True)
        temp_out.unlink(missing_ok=True)
    return None


def _download_direct_url(
    url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Downloads files from generic HTTP/HTTPS links (Mediafire, Dropbox, Mega, direct mirrors)."""
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)
    if log_cb:
        log_cb(f"  [Direct Mirror] Downloading from URL: {url[:70]}...")
    s = cloudscraper.create_scraper()
    s.headers.update({"User-Agent": FEED_UA})
    try:
        r = s.get(url, stream=True, timeout=60, allow_redirects=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "text/html" in ct and int(r.headers.get("Content-Length", 0) or 0) < 50000:
            soup = bs(r.text, "html.parser")
            direct_a = soup.select_one("a#downloadButton, a.download_link, a[href*='download']")
            if direct_a and direct_a.get("href"):
                next_url = direct_a["href"]
                if next_url.startswith("http"):
                    return _download_direct_url(next_url, dest_path, progress_cb, log_cb, cancel_event)
            return None

        cd = r.headers.get("Content-Disposition", "")
        fallback = Path(url.split("?")[0]).name or "model.zip"
        return _stream_response_to_file(r, dest_path, fallback, progress_cb, cancel_event)
    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("Direct URL download error: %s", e)
    return None


def _download_from_gdrive(
    page,
    gdrive_url,
    dest_path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    """
    Downloads model archive using all available methods in sequence without prompting the user:
    1. Direct HTTP CloudScraper Stream
    2. Google Drive API Quota Bypass (if credentials present)
    3. Playwright Browser Interactive Automation
    4. Browser Session Cookie Handshake
    5. System Curl Engine
    6. Generic Direct URL Downloader (for non-GDrive mirrors)
    """
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    # 1. Generic non-GDrive URL check (Mediafire, Dropbox, Mega, direct CDN)
    if "drive.google.com" not in gdrive_url and "google.com" not in gdrive_url:
        res = _download_direct_url(gdrive_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

    # 2. Extract Google Drive file_id
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", gdrive_url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", gdrive_url)
    if not m:
        return _download_direct_url(gdrive_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
    file_id = m.group(1)

    # Setup temporary browser if page not passed
    owns_page = False
    browser_cleanup = None
    if page is None:
        try:
            from browser_manager import BrowserManager
            from config import HEADLESS
            bm = BrowserManager(headless=HEADLESS)
            p_ctx, ctx = bm.get_context()
            page = ctx.new_page()
            owns_page = True
            browser_cleanup = lambda: (ctx.close(), p_ctx.stop())
        except Exception as bm_err:
            logger.debug("Could not spawn standalone browser context: %s", bm_err)

    try:
        # Check user preference for GDrive API
        prefer_api = False
        try:
            from desktop.backend.settings_manager import settings_manager
            prefer_api = settings_manager.get_prefer_gdrive_api()
        except Exception:
            pass

        # Strategy A: Google Drive API if explicitly preferred and configured
        if prefer_api:
            try:
                from gdrive_api import check_gdrive_status, copy_and_download
                status = check_gdrive_status()
                if status.get("credentials_present") and status.get("authenticated"):
                    if log_cb:
                        log_cb("  [Method: GDrive API] Preferred API download...")
                    res = copy_and_download(file_id, dest_path, log_cb=log_cb, progress_cb=progress_cb, cancel_event=cancel_event)
                    if res:
                        return res
            except Exception:
                pass

        # Strategy 1: Direct High-Speed CloudScraper Stream
        if log_cb:
            log_cb("  [Method 1/5] Direct high-speed download stream...")
        res = _download_req(file_id, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

        # Strategy 2: Google Drive API Quota Bypass (silent fallback if credentials present)
        try:
            from gdrive_api import check_gdrive_status, copy_and_download
            status = check_gdrive_status()
            if status.get("credentials_present") and status.get("authenticated"):
                if log_cb:
                    log_cb("  [Method 2/5] Google Drive API quota bypass...")
                logger.info("Attempting Drive API quota bypass for %s", file_id)
                res = copy_and_download(file_id, dest_path, log_cb=log_cb, progress_cb=progress_cb, cancel_event=cancel_event)
                if res:
                    return res
        except Exception:
            pass

        # Strategy 3: Playwright Browser Full Automation
        if page:
            if log_cb:
                log_cb("  [Method 3/5] Playwright browser automation...")
            res = _download_pw_full(page, file_id, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
            if res:
                return res

        # Strategy 4: Browser Session Cookie Handshake
        if page:
            if log_cb:
                log_cb("  [Method 4/5] Browser session cookie stream...")
            res = _download_browser_cookies(page, file_id, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
            if res:
                return res

        # Strategy 5: System Curl Engine
        if log_cb:
            log_cb("  [Method 5/5] Native curl session engine...")
        res = _download_curl(file_id, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

        if log_cb:
            log_cb("  ✗ All automated download methods attempted")
        return None

    finally:
        if owns_page and browser_cleanup:
            try:
                browser_cleanup()
            except Exception:
                pass
