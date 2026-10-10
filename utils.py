import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse
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


def decide_download_method(url: Optional[str]) -> str:
    """
    Decides and returns the download method identifier for a given target URL:
    - 'gdrive': Google Drive (drive.google.com, docs.google.com)
    - 'fshare': Fshare.vn (fshare.vn)
    - 'sharepoint': Microsoft SharePoint (sharepoint.com)
    - 'onedrive': Microsoft OneDrive (1drv.ms, onedrive.live.com, onedrive.com)
    - 'direct': Direct HTTP links / mirrors (MediaFire, Mega, Dropbox, or generic direct HTTP/HTTPS)
    """
    if not url:
        return "direct"
    u = str(url).lower()
    if "fshare.vn" in u:
        return "fshare"
    if "sharepoint.com" in u:
        return "sharepoint"
    if "1drv.ms" in u or "onedrive.live.com" in u or "onedrive.com" in u:
        return "onedrive"
    if "drive.google.com" in u or "docs.google.com" in u:
        return "gdrive"
    if "google.com" in u and ("id=" in u or "/file/d/" in u or "export=download" in u):
        return "gdrive"
    return "direct"


def detect_download_provider(url: Optional[str]) -> str:
    """Identifies the human-readable hosting platform / download provider from a URL."""
    if not url:
        return ""
    m = decide_download_method(url)
    if m == "gdrive":
        return "Google Drive"
    if m == "fshare":
        return "Fshare"
    if m == "sharepoint":
        return "SharePoint"
    if m == "onedrive":
        return "OneDrive"
    u = str(url).lower()
    if "mediafire.com" in u:
        return "MediaFire"
    if "mega.nz" in u or "mega.io" in u:
        return "Mega"
    if "dropbox.com" in u:
        return "Dropbox"
    if "link.cgtips.org" in u:
        return "CGTips Locker"
    return "Direct"


def resolve_gdrive_from_locker(page, locker_url):
    """Loads content locker page with Playwright and extracts Google Drive, Fshare, SharePoint, or mirror destination URL."""
    try:
        page.goto(locker_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        # Check for immediate link
        dl_url = page.evaluate("""() => {
            const btn = document.querySelector('.download_dem a.btn, a.btn-download, a#download-btn');
            if (btn && btn.href && btn.href.startsWith('http')) return btn.href;
            const mirrors = ['drive.google.com', 'fshare.vn', 'sharepoint.com', 'onedrive.live.com', '1drv.ms', 'mediafire.com', 'mega.nz', 'dropbox.com'];
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
                const mirrors = ['drive.google.com', 'fshare.vn', 'sharepoint.com', 'onedrive.live.com', '1drv.ms', 'mediafire.com', 'mega.nz', 'dropbox.com'];
                const anyMirror = Array.from(document.querySelectorAll('a')).map(a => a.href).find(h => h && mirrors.some(m => h.includes(m)));
                return anyMirror || null;
            }""")

        return dl_url
    except Exception as e:
        logger.warning("Failed to resolve locker %s: %s", locker_url, e)
        return None


resolve_destination_from_locker = resolve_gdrive_from_locker


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


def _download_fshare_guest(
    fshare_url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 1: Fshare Guest API direct HTTP session."""
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    m = re.search(r"/file/([a-zA-Z0-9]+)", fshare_url)
    linkcode = m.group(1) if m else None
    if not linkcode:
        return None

    if log_cb:
        log_cb("  [Fshare Method 1/4] Guest API: Fetching session & token...")

    target_url = fshare_url if fshare_url.startswith("http") else f"https://{fshare_url}"
    clean_url = f"https://www.fshare.vn/file/{linkcode}"
    s = cloudscraper.create_scraper()
    s.headers.update({
        "User-Agent": FEED_UA,
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    })

    try:
        if cancel_event and cancel_event.is_set():
            raise DownloadPaused()

        r1 = s.get(target_url, timeout=30)
        r1.raise_for_status()
        soup = bs(r1.text, "html.parser")
        form = soup.find("form", id="form-download")
        if not form:
            return None

        csrf_input = form.find("input", attrs={"name": "_csrf-app"})
        csrf = csrf_input.get("value") if csrf_input else ""
        if not csrf:
            return None

        post_data = {
            "_csrf-app": csrf,
            "linkcode": linkcode,
            "withFcode5": "0",
        }
        post_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": clean_url,
        }

        r2 = s.post("https://www.fshare.vn/download/get", data=post_data, headers=post_headers, timeout=30)
        r2.raise_for_status()
        data = r2.json()

        redirect_url = data.get("url")
        if not redirect_url:
            if log_cb and "errors" in data:
                log_cb(f"  [Fshare Guest API] Token error: {data.get('errors')}")
            return None

        wait_time = int(data.get("wait_time", 60))
        fallback_name = data.get("name") or f"{linkcode}.rar"

        if log_cb:
            log_cb(f"  [Fshare Method 1/4] Waiting {wait_time}s countdown for '{fallback_name}'...")

        step = 1.0
        elapsed = 0.0
        last_log = time.monotonic()
        while elapsed < wait_time + 1.5:
            if cancel_event and cancel_event.is_set():
                raise DownloadPaused()
            time.sleep(step)
            elapsed += step
            remaining = max(0, int(wait_time - elapsed))
            if time.monotonic() - last_log >= 10 and log_cb:
                log_cb(f"  [Fshare Countdown] {remaining}s remaining...")
                last_log = time.monotonic()

        if log_cb:
            log_cb("  [Fshare Method 1/4] Resolving direct CDN download stream...")

        r3 = s.get(redirect_url, allow_redirects=False, timeout=30)
        cdn_url = r3.headers.get("Location") if r3.status_code in (301, 302) else None
        if not cdn_url:
            if log_cb:
                log_cb(f"  [Fshare Guest API] Redirect failed with HTTP {r3.status_code}")
            return None

        if log_cb:
            log_cb("  [Fshare Method 1/4] ✓ CDN URL acquired, streaming model file...")

        # Fshare CDN rejects requests containing a Referer header with HTTP 503.
        # Direct stream without Referer header.
        cdn_headers = {
            "User-Agent": FEED_UA,
            "Accept": "*/*",
        }
        r4 = requests.get(cdn_url, headers=cdn_headers, stream=True, timeout=60)
        r4.raise_for_status()

        return _stream_response_to_file(r4, dest_path, fallback_name, progress_cb, cancel_event)

    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("Fshare Guest API failed for %s: %s", fshare_url, e)
        if log_cb:
            log_cb(f"  [Fshare Guest API] {e}")
        return None


def _download_fshare_playwright(
    page,
    fshare_url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 2: Interactive Playwright browser automation for Fshare."""
    if not page:
        return None
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)
    if log_cb:
        log_cb("  [Fshare Method 2/4] Playwright browser: Navigating and clicking download...")

    try:
        page.goto(fshare_url, timeout=35000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        dl_info = page.evaluate("""() => {
            const chk = document.querySelector("#policy-checkbox");
            if (chk) chk.checked = true;
            if (typeof $ !== "undefined") {
                $("#policy-checkbox").prop("checked", true);
            }
            const btn = document.querySelector("#download-free, .btn_guest_free_download, .btn-download-free");
            if (!btn) return {found: false};
            if (typeof downloadFile === "function") {
                downloadFile(btn);
                return {found: true, called: true};
            }
            btn.click();
            return {found: true, called: false};
        }""")

        if not dl_info or not dl_info.get("found"):
            if log_cb:
                log_cb("  [Fshare Browser] Download button not found on page")
            return None

        countdown_secs = 65
        for _ in range(10):
            wait_text = page.evaluate("""() => {
                const el = document.querySelector(".content_waiting_time, .wait-to-download, h2");
                return el ? el.textContent : "";
            }""")
            m = re.search(r"(\d+)\s*(?:s|giây|second)", wait_text or "", re.IGNORECASE)
            if m:
                countdown_secs = int(m.group(1)) + 3
                break
            page.wait_for_timeout(1000)

        if log_cb:
            log_cb(f"  [Fshare Method 2/4] Waiting {countdown_secs}s countdown in browser...")

        start_t = time.monotonic()
        while time.monotonic() - start_t < countdown_secs:
            if cancel_event and cancel_event.is_set():
                raise DownloadPaused()
            page.wait_for_timeout(2000)

        # Check if direct CDN redirect link was captured into window.backupDownLink
        backup_link = page.evaluate("() => typeof backupDownLink !== 'undefined' ? backupDownLink : null")
        if backup_link and str(backup_link).startswith("http"):
            try:
                r_redir = requests.get(str(backup_link), allow_redirects=False, timeout=30)
                cdn_loc = r_redir.headers.get("Location") if r_redir.status_code in (301, 302) else None
                if cdn_loc:
                    cdn_headers = {"User-Agent": FEED_UA, "Accept": "*/*"}
                    r_stream = requests.get(cdn_loc, headers=cdn_headers, stream=True, timeout=60)
                    if r_stream.status_code in (200, 206):
                        fallback = Path(fshare_url.rstrip("/").split("?")[0]).name + ".rar"
                        res_file = _stream_response_to_file(r_stream, dest_path, fallback, progress_cb, cancel_event)
                        if res_file:
                            if log_cb:
                                log_cb(f"  [Fshare Method 2/4] ✓ Playwright CDN stream completed: {Path(res_file).name}")
                            return res_file
            except Exception as stream_err:
                logger.debug("Playwright backupDownLink stream fallback error: %s", stream_err)

        try:
            with page.expect_download(timeout=25000) as dl_event:
                page.evaluate("""() => {
                    const retryBtn = document.querySelector(".cus_down_end_countdown a, .download-btn, #download-btn");
                    if (retryBtn) retryBtn.click();
                    if (typeof afterWait_New === "function" && typeof backupDownLink !== "undefined" && backupDownLink) {
                        window.location.href = backupDownLink;
                    }
                }""")
            dl = dl_event.value
            name = dl.suggested_filename or f"fshare_model_{int(time.time())}.rar"
            target_file = dest_path / name
            dl.save_as(str(target_file))

            if target_file.exists() and target_file.stat().st_size > 5000:
                if log_cb:
                    log_cb(f"  [Fshare Method 2/4] ✓ Playwright download completed: {name}")
                return str(target_file)
        except Exception:
            pass

    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("Playwright Fshare error for %s: %s", fshare_url, e)
        if log_cb:
            log_cb(f"  [Fshare Browser] {e}")
    return None


def _download_fshare_ytdlp(
    fshare_url: str,
    dest_path: Path,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 3: yt-dlp CLI / engine extraction for Fshare."""
    try:
        import yt_dlp
    except ImportError:
        return None

    if log_cb:
        log_cb("  [Fshare Method 3/4] Trying yt-dlp engine...")

    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)
    before_files = set(dest_path.iterdir())

    ydl_opts = {
        "outtmpl": str(dest_path / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([fshare_url])
        after_files = set(dest_path.iterdir()) - before_files
        for f in after_files:
            if f.is_file() and f.stat().st_size > 5000:
                if log_cb:
                    log_cb(f"  [Fshare Method 3/4] ✓ yt-dlp succeeded: {f.name}")
                return str(f)
    except Exception as e:
        logger.debug("yt-dlp failed for %s: %s", fshare_url, e)
    return None


def _download_fshare_cookies(
    page,
    fshare_url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 4: Replay cookies and captured source tokens from active browser context."""
    if not page:
        return None
    try:
        cookies = page.context.cookies(["https://www.fshare.vn", "https://fshare.vn"])
        if not cookies:
            return None
        if log_cb:
            log_cb("  [Fshare Method 4/4] Cookie session replay from browser...")

        s = cloudscraper.create_scraper()
        s.headers.update({"User-Agent": FEED_UA})
        for c in cookies:
            s.cookies.set(c["name"], c["value"], domain=c.get("domain", ".fshare.vn"), path=c.get("path", "/"))

        direct_link = page.evaluate("() => typeof backupDownLink !== 'undefined' ? backupDownLink : null")
        if direct_link and str(direct_link).startswith("http"):
            r = s.get(direct_link, allow_redirects=False, timeout=30)
            if r.status_code in (301, 302) and r.headers.get("Location"):
                r_stream = s.get(r.headers["Location"], stream=True, timeout=60)
                if r_stream.status_code in (200, 206):
                    fallback = Path(fshare_url.rstrip("/")).name + ".rar"
                    return _stream_response_to_file(r_stream, dest_path, fallback, progress_cb, cancel_event)
    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("Fshare cookie handshake error: %s", e)
    return None


def download_from_fshare(
    page_or_url,
    fshare_url_or_dest = None,
    dest_path = None,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """
    Downloads model archive from Fshare.vn across multiple methods:
    1. Fshare Guest API (Fast HTTP session with countdown & CDN stream)
    2. Playwright Interactive Browser Automation
    3. yt-dlp CLI / Engine
    4. Browser Session Cookie & DOM Handshake

    Can be called either as:
        download_from_fshare(page, fshare_url, dest_path, ...)
    or:
        download_from_fshare(fshare_url, dest_path, ...)
    """
    if isinstance(page_or_url, (str, Path)) and (dest_path is None or not isinstance(dest_path, (str, Path))):
        page = None
        fshare_url = str(page_or_url)
        dest_path = Path(fshare_url_or_dest)
    else:
        page = page_or_url
        fshare_url = str(fshare_url_or_dest)
        dest_path = Path(dest_path)

    dest_path.mkdir(parents=True, exist_ok=True)
    if log_cb:
        log_cb(f"Starting Fshare download pipeline for: {fshare_url}")

    # Method 1: Guest API (Fast HTTP session with countdown & direct CDN stream)
    res = _download_fshare_guest(fshare_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
    if res:
        return res

    # Method 2: Playwright Interactive Automation (if caller provided a page)
    if page:
        res = _download_fshare_playwright(page, fshare_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

    # Method 3: yt-dlp CLI / Engine
    res = _download_fshare_ytdlp(fshare_url, dest_path, log_cb=log_cb, cancel_event=cancel_event)
    if res:
        return res

    # Method 4: Browser Session Cookie Handshake (if caller provided a page)
    if page:
        res = _download_fshare_cookies(page, fshare_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

    # Method 5: Standalone Playwright browser fallback if caller did not supply a page
    if not page:
        try:
            from browser_manager import BrowserManager
            from config import HEADLESS
            bm = BrowserManager(headless=HEADLESS)
            p_ctx, ctx = bm.get_context()
            try:
                standalone_page = ctx.new_page()
                res = _download_fshare_playwright(standalone_page, fshare_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
                if res:
                    return res
                res = _download_fshare_cookies(standalone_page, fshare_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
                if res:
                    return res
            finally:
                ctx.close()
                p_ctx.stop()
        except Exception as bm_err:
            logger.debug("Standalone browser fallback error for Fshare: %s", bm_err)

    if log_cb:
        log_cb("  ✗ All Fshare download methods attempted")
    return None


def _normalize_sharepoint_download_url(url: str) -> str:
    """Ensures SharePoint sharing links have download=1 parameter."""
    u = (url or "").strip()
    if "download=1" in u:
        return u
    sep = "&" if "?" in u else "?"
    return f"{u}{sep}download=1"


def _extract_sharepoint_filename(cd: str, final_url: str, default: str = "sharepoint_model.rar") -> str:
    """Parses model filename from Content-Disposition header or redirect URL path."""
    if cd:
        m = re.search(r"filename\*=utf-8''([^;\r\n]+)", cd, re.IGNORECASE)
        if m:
            try:
                return urllib.parse.unquote(m.group(1)).strip().strip('"\'')
            except Exception:
                pass
        m = re.search(r'filename="?([^";\r\n]+)"?', cd, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if "%" in val:
                try:
                    val = urllib.parse.unquote(val)
                except Exception:
                    pass
            return val

    # Fallback to URL path
    if final_url:
        path = urllib.parse.urlparse(final_url).path
        name = path.split("/")[-1]
        if name and "." in name:
            try:
                name = urllib.parse.unquote(name).strip()
                if any(name.lower().endswith(ext) for ext in [".zip", ".rar", ".7z", ".skp"]):
                    return name
            except Exception:
                pass
    return default


def _download_sharepoint_stream(
    url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 1: Direct authenticated session stream with cookie persistence across 302 redirects."""
    dl_url = _normalize_sharepoint_download_url(url)
    if log_cb:
        log_cb("  [SharePoint Method 1/3] Direct HTTP stream with session cookies...")

    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        r = s.get(dl_url, stream=True, timeout=60, allow_redirects=True)
        ct = r.headers.get("Content-Type", "").lower()
        if r.status_code in (200, 206) and "text/html" not in ct:
            filename = _extract_sharepoint_filename(r.headers.get("Content-Disposition", ""), r.url)
            if log_cb:
                log_cb(f"  [SharePoint] Streaming archive: {filename}")
            return _stream_response_to_file(r, dest_path, filename, progress_cb, cancel_event)
        elif "text/html" in ct and log_cb:
            log_cb("  [SharePoint Stream] Received HTML page instead of binary payload")
    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("SharePoint stream error: %s", e)
        if log_cb:
            log_cb(f"  [SharePoint Stream] Error: {e}")
    return None


def _download_sharepoint_playwright(
    page,
    url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """
    Method 1: Playwright browser interactive automation.
    Navigates to the SharePoint page, clicks the exact download button element:
    <span class="ms-Button-flexContainer flexContainer-53" data-automationid="splitbuttonprimary"><i data-icon-name="Download"...>
    and streams the authenticated download payload.
    """
    if not page:
        return None
    if log_cb:
        log_cb("  [SharePoint Method 1/3] Playwright browser: Interacting with download button...")

    try:
        # Navigate to SharePoint view page
        page.goto(url, timeout=35000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # Locate download button using explicit user selector hierarchy:
        # 1. Exact split button container span
        # 2. Exact download icon
        # 3. Parent command button / commandBar items
        selectors_to_check = [
            '[data-automationid="splitbuttonprimary"]',
            'i[data-icon-name="Download"]',
            'button:has([data-automationid="splitbuttonprimary"])',
            'button:has(i[data-icon-name="Download"])',
            '#downloadCommand',
            '[data-automation-id="downloadCommand"]',
            'button[aria-label*="Download" i]',
            'button[name*="Download" i]',
        ]

        found_selector = None
        for sel in selectors_to_check:
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=3000)
                if el:
                    found_selector = sel
                    break
            except Exception:
                continue

        if not found_selector:
            for sel in selectors_to_check:
                if page.query_selector(sel):
                    found_selector = sel
                    break

        if log_cb and found_selector:
            log_cb(f"  [SharePoint Browser] Download button ready ({found_selector})")

        with page.expect_download(timeout=35000) as dl_event:
            clicked = False
            try:
                clicked = page.evaluate('''() => {
                    const split = document.querySelector('[data-automationid="splitbuttonprimary"]')
                        || document.querySelector('i[data-icon-name="Download"]');
                    if (split) {
                        const btn = split.closest('button, [role="button"]') || split;
                        btn.click();
                        return true;
                    }
                    const cmd = document.querySelector('#downloadCommand, [data-automation-id="downloadCommand"]');
                    if (cmd) {
                        cmd.click();
                        return true;
                    }
                    return false;
                }''')
            except Exception:
                pass

            if not clicked:
                target = page.locator(found_selector or '[data-automationid="splitbuttonprimary"]').first
                target.click()

        dl = dl_event.value
        filename = dl.suggested_filename or f"sharepoint_model_{int(time.time())}.rar"
        dl_url = getattr(dl, "url", None)

        if log_cb:
            log_cb(f"  [SharePoint Browser] Captured download trigger: {filename}")

        # Stream directly using authenticated browser session cookies for real-time progress callbacks
        cookies = {}
        try:
            cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        except Exception:
            pass

        if dl_url and cookies:
            try:
                s = requests.Session()
                s.cookies.update(cookies)
                s.headers.update({
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                    "Referer": url,
                })
                r = s.get(dl_url, stream=True, timeout=60)
                ct = r.headers.get("Content-Type", "").lower()
                if r.status_code in (200, 206) and "text/html" not in ct:
                    if log_cb:
                        log_cb(f"  [SharePoint Stream] Streaming {filename} with progress...")
                    out_path = _stream_response_to_file(r, dest_path, filename, progress_cb, cancel_event)
                    if out_path and Path(out_path).exists() and Path(out_path).stat().st_size > 5000:
                        if log_cb:
                            log_cb(f"  [SharePoint Browser] ✓ Successfully downloaded: {filename}")
                        return out_path
            except DownloadPaused:
                raise
            except Exception as stream_err:
                logger.debug("SharePoint stream with browser cookies failed: %s", stream_err)

        # Fallback to direct Playwright save_as
        target_file = dest_path / filename
        dl.save_as(str(target_file))
        if target_file.exists() and target_file.stat().st_size > 5000:
            if log_cb:
                log_cb(f"  [SharePoint Browser] ✓ Saved file: {filename}")
            return str(target_file)

    except DownloadPaused:
        raise
    except Exception as e:
        logger.debug("SharePoint Playwright download error: %s", e)
        if log_cb:
            log_cb(f"  [SharePoint Browser] Error: {e}")
    return None


def _download_sharepoint_curl(
    url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """Method 3: System Curl CLI with session cookiejar."""
    if not shutil.which("curl"):
        return None
    dl_url = _normalize_sharepoint_download_url(url)
    if log_cb:
        log_cb("  [SharePoint Method 3/3] System Curl CLI with session cookiejar...")

    cookie_file = dest_path / f".sp_cookie_{threading.get_ident()}.txt"
    temp_out = dest_path / f".sp_temp_{threading.get_ident()}.bin"
    try:
        cmd = [
            "curl", "-s", "-L",
            "-c", str(cookie_file),
            "-b", str(cookie_file),
            "-A", USER_AGENT,
            "--max-time", "600",
            dl_url,
            "-o", str(temp_out),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=620)
        if temp_out.exists() and temp_out.stat().st_size > 10000:
            with open(temp_out, "rb") as f:
                head = f.read(512)
            if not head.startswith(b"<!DOCTYPE") and not head.startswith(b"<html"):
                final_name = f"sharepoint_model_{int(time.time())}.rar"
                final_path = dest_path / final_name
                os.replace(temp_out, final_path)
                if log_cb:
                    log_cb(f"  [SharePoint Curl] ✓ Successfully downloaded: {final_name}")
                return str(final_path)
    except Exception as e:
        logger.debug("SharePoint curl error: %s", e)
    finally:
        cookie_file.unlink(missing_ok=True)
        temp_out.unlink(missing_ok=True)
    return None


def download_from_sharepoint(
    page_or_url,
    sharepoint_url_or_dest = None,
    dest_path = None,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """
    Downloads model archive from cgtips-my.sharepoint.com (SharePoint / OneDrive for Business):
    1. Playwright interactive browser automation clicking the download button
       (<span data-automationid="splitbuttonprimary"><i data-icon-name="Download">)
    2. Authenticated HTTP session stream with automatic FedAuth cookie tracking across 302 redirects
    3. System Curl CLI engine with cookie jar

    Supports calling as:
        download_from_sharepoint(page, url, dest_path, ...)
    or:
        download_from_sharepoint(url, dest_path, ...)
    """
    if isinstance(page_or_url, (str, Path)) and (dest_path is None or not isinstance(dest_path, (str, Path))):
        page = None
        sp_url = str(page_or_url)
        dest_path = Path(sharepoint_url_or_dest)
    else:
        page = page_or_url
        sp_url = str(sharepoint_url_or_dest)
        dest_path = Path(dest_path)

    dest_path.mkdir(parents=True, exist_ok=True)
    if log_cb:
        log_cb(f"Starting SharePoint download pipeline for: {sp_url[:75]}...")

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
            logger.debug("Could not spawn standalone browser context for SharePoint: %s", bm_err)

    try:
        # Method 1: Playwright interactive browser automation with download button click
        if page:
            res = _download_sharepoint_playwright(page, sp_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
            if res:
                return res

        # Method 2: Direct HTTP stream
        res = _download_sharepoint_stream(sp_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

        # Method 3: System Curl
        res = _download_sharepoint_curl(sp_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res

        if log_cb:
            log_cb("  ✗ All SharePoint download methods attempted")
        return None
    finally:
        if owns_page and browser_cleanup:
            try:
                browser_cleanup()
            except Exception:
                pass


def download_model(
    page,
    target_url: str,
    dest_path: Path,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[str]:
    """
    Intelligent Multi-Provider Model Download Dispatcher / Decision Engine:
    Decides and routes to the appropriate download pipeline based on URL pattern matching:
    1. Fshare (fshare.vn) -> download_from_fshare
    2. SharePoint / OneDrive (sharepoint.com, onedrive.live.com, 1drv.ms) -> download_from_sharepoint
    3. Google Drive (drive.google.com, docs.google.com) -> Multi-tier Google Drive pipeline
    4. Direct HTTP Mirror (Mediafire, Mega, Dropbox, or generic direct HTTP/HTTPS) -> _download_direct_url
    """
    dest_path = Path(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    method = decide_download_method(target_url)
    provider_name = detect_download_provider(target_url)

    if log_cb:
        log_cb(f"  [Decision Engine] Identified provider: {provider_name} ({method}) for {str(target_url)[:70]}...")

    # Route 1: Fshare.vn download pipeline
    if method == "fshare":
        res = download_from_fshare(page, target_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res
        return None

    # Route 2: SharePoint / OneDrive download pipeline
    if method in ("sharepoint", "onedrive"):
        res = download_from_sharepoint(page, target_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res
        return None

    # Route 3: Generic non-GDrive URL check (Mediafire, Dropbox, Mega, direct CDN)
    if method != "gdrive":
        res = _download_direct_url(target_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
        if res:
            return res
        return None

    # Route 4: Google Drive pipeline
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", target_url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", target_url)
    if not m:
        return _download_direct_url(target_url, dest_path, progress_cb=progress_cb, log_cb=log_cb, cancel_event=cancel_event)
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


# Alias for backwards compatibility
_download_from_gdrive = download_model
