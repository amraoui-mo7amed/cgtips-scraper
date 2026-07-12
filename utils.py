import logging
import re
import time
import cloudscraper
import requests
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin
from decouple import config
from tqdm import tqdm

logger = logging.getLogger("utils")

FEED_UA = config("USER_AGENT")

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

        soup = bs(resp.content, "xml")
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

        time.sleep(0.5)

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

        time.sleep(0.5)

    return all_entries


def extract_download_url(article_url, retries=3):
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
                time.sleep(2)
    return None


def download_from_locker(page, locker_url, dest_path):
    try:
        page.goto(locker_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        gdrive_url = page.evaluate("""() => {
            const btn = document.querySelector('.download_dem a.btn');
            return btn ? btn.href : null;
        }""")

        if not gdrive_url or "drive.google.com" not in gdrive_url:
            return None

        return _download_from_gdrive(page, gdrive_url, dest_path)
    except Exception as e:
        return None


def _download_req(file_id, dest_path):
    s = cloudscraper.create_scraper()
    s.headers.update({"User-Agent": FEED_UA})
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

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

    path = dest_path / name
    total = int(r.headers.get("Content-Length", 0))
    with open(path, "wb") as f:
        with tqdm(total=total, unit='B', unit_scale=True, desc=name[:40], leave=False) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    return str(path)


def _download_pw(page, file_id, dest_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

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


def _download_from_gdrive(page, gdrive_url, dest_path):
    m = re.search(r"/file/d/([^/]+)", gdrive_url)
    if not m:
        return None
    file_id = m.group(1)
    dest_path.mkdir(parents=True, exist_ok=True)

    result = _download_req(file_id, dest_path)
    if result:
        return result

    try:
        from gdrive_api import copy_and_download
        result = copy_and_download(file_id, dest_path)
        if result:
            return result
    except Exception:
        pass

    result = _download_pw(page, file_id, dest_path)
    return result
