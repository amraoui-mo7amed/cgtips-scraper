import logging
import json
import os
import re
import requests
from pathlib import Path
from tqdm import tqdm
from scraper import Scraper
from utils import get_feed, extract_download_url, download_from_locker

logging.basicConfig(
    level=logging.WARNING,
    format="[%(levelname)s] %(message)s",
)
for name in ("main", "utils", "scraper", "gdrive_api"):
    logging.getLogger(name).setLevel(logging.INFO)
logger = logging.getLogger("main")

CATEGORIES_FILE = "categories.json"
IMAGES_DIR = Path("feeds")
BRAVE_USER_DATA = os.path.join(os.environ["LOCALAPPDATA"], "BraveSoftware", "Brave-Browser", "User Data")
CHROME_USER_DATA = os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data")
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})


def load_categories():
    if os.path.exists(CATEGORIES_FILE):
        logger.info("Loading categories from %s", CATEGORIES_FILE)
        with open(CATEGORIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    logger.info("Scraping categories (no cache found)")
    scraper = Scraper()
    cats = scraper.get_categories()
    if cats:
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cats, f, ensure_ascii=False, indent=4)
        logger.info("Saved %d categories to %s", len(cats), CATEGORIES_FILE)
    return cats


def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" .")


def load_cache():
    if not os.path.exists("selected_feeds.json"):
        return {}
    try:
        with open("selected_feeds.json", encoding="utf-8") as f:
            data = json.load(f)
        cache = {}
        for group in data.get("selected", []):
            for entry in group.get("feed_entries", []):
                link = entry.get("link")
                if link:
                    cache[link] = entry
        logger.info("Loaded %d cached entries", len(cache))
        return cache
    except Exception as e:
        logger.warning("Failed to load cache: %s", e)
        return {}


def download_images(page, entry, folder):
    link = entry["link"]
    title = entry["title"]
    safe_title = sanitize(title)[:80].rstrip(" .")
    dest = folder / safe_title
    dest.mkdir(parents=True, exist_ok=True)

    cached = entry.get("downloaded_images", [])
    if cached and all(os.path.exists(p) for p in cached):
        logger.info("  All %d images cached for '%s'", len(cached), safe_title[:40])
        return cached, entry.get("download_url")

    logger.info("  Fetching article: %s", link[:70])
    try:
        page.goto(link, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
    except Exception as e:
        logger.warning("  Failed to load %s: %s", link[:50], e)
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
            logger.debug("    Saved: %s", name)
        except Exception as e:
            logger.debug("    Skipped %s: %s", src[:50], e)

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

    logger.info("  Downloaded %d images for '%s'", len(downloaded), safe_title[:40])
    if download_url:
        logger.info("  Download link: %s", download_url[:60])
    return downloaded, download_url


if __name__ == "__main__":
    logger.info("=== Interactive Feed Fetcher ===")

    categories = load_categories()
    if not categories:
        logger.error("No categories found")
        exit(1)

    print("\n--- Step 1: Select a category ---")
    for i, cat in enumerate(categories, 1):
        heading = cat.get("heading", {})
        print(f"  [{i}] {heading.get('name', 'Unknown')}")

    while True:
        try:
            cat_idx = int(input("\nCategory number: ").strip()) - 1
            if 0 <= cat_idx < len(categories):
                break
        except ValueError:
            pass
        print("Invalid. Try again.")

    selected_cat = categories[cat_idx]
    subs = selected_cat.get("subcategories", [])
    heading = selected_cat.get("heading", {})
    cat_name = heading.get("name", "Unknown")
    cat_safe = sanitize(cat_name)

    print(f"\n--- Step 2: Select subcategories from '{cat_name}' ---")
    print("  [0] All subcategories")
    for j, sub in enumerate(subs, 1):
        print(f"  [{j}] {sub['name']}")

    while True:
        raw = input("\nSubcategory number(s) (e.g. 1 or 1,3,5 or 0 for all): ").strip()
        if raw == "0":
            selected_subs = list(range(len(subs)))
            break
        indices = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                idx = int(token) - 1
                if 0 <= idx < len(subs):
                    indices.append(idx)
            except ValueError:
                pass
        if indices:
            selected_subs = indices
            break
        print("Invalid. Try again.")

    while True:
        try:
            max_items = int(input("\nMax items to process per feed (0 = all): ").strip() or "0")
            break
        except ValueError:
            pass

    download_choice = input("Download images from articles? (y/N): ").strip().lower()

    urls_to_fetch = []
    for idx in selected_subs:
        sub = subs[idx]
        urls_to_fetch.append(("subcategory", sub["name"], sub["feed_url"]))

    scraper = Scraper()
    context = None
    p_ctx = None
    page = None
    import subprocess
    from playwright.sync_api import sync_playwright
    from scraper import BRAVE_PATH, CHROME_PATH

    browsers_to_try = [
        ("Brave", BRAVE_PATH, BRAVE_USER_DATA, "brave.exe"),
        ("Chrome", CHROME_PATH, CHROME_USER_DATA, "chrome.exe"),
    ]
    context = None
    p_ctx = None
    page = None
    for name, exe_path, user_data_dir, exe_name in browsers_to_try:
        try:
            result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}"], capture_output=True, text=True)
            if exe_name in result.stdout:
                print(f"\n⚠️  {name} is running. Close it first, then press Enter to continue...")
                input()
            p_ctx = sync_playwright().start()
            context = p_ctx.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path=exe_path,
                headless=True,
            )
            page = context.pages[0] if context.pages else context.new_page()
            logger.info("Using %s browser", name)
            break
        except Exception as e:
            logger.warning("Failed to launch %s: %s", name, e)
            if p_ctx:
                p_ctx.stop()
                p_ctx = None
            continue

    if context is None:
        logger.error("No browser available (tried Brave and Chrome)")
        exit(1)

    cache = load_cache()
    all_data = []
    for kind, name, url in urls_to_fetch:
        print(f"\n--- {kind}: {name} ---")
        feed = get_feed(url, max_items=max_items, page=page)

        name_safe = sanitize(name)
        folder = IMAGES_DIR / cat_safe / name_safe

        for entry in feed:
            cached = cache.get(entry["link"])
            entry["downloaded_images"] = (cached or {}).get("downloaded_images", [])
            entry["download_url"] = (cached or {}).get("download_url")
            entry["model_file"] = (cached or {}).get("model_file")

            need_model = not (entry["model_file"] and os.path.exists(entry["model_file"]))
            need_images = (download_choice == "y") and not (
                entry.get("downloaded_images") and all(os.path.exists(p) for p in entry["downloaded_images"])
            )

            if not need_model and not need_images:
                tqdm.write(f"  [+] {entry['title'][:60]} (cached)")
                continue

            if need_model and not entry["download_url"]:
                entry["download_url"] = extract_download_url(entry["link"])

            if need_model and entry["download_url"]:
                title_piece = sanitize(entry["title"])[:80].rstrip(" .")
                model_folder = folder / title_piece / "model"
                result = download_from_locker(page, entry["download_url"], model_folder)
                entry["model_file"] = result
                if result:
                    tqdm.write(f"  [+] {Path(result).name}")
                else:
                    tqdm.write(f"  [-] download failed")
            elif need_model and not entry["download_url"]:
                tqdm.write(f"  [?] no locker link")

            if need_images:
                imgs, dl_url = download_images(page, entry, folder)
                entry["downloaded_images"] = imgs
                if dl_url and not entry.get("download_url"):
                    entry["download_url"] = dl_url

        all_data.append({"kind": kind, "name": name, "url": url, "feed_entries": feed})

    if page:
        context.close()
        p_ctx.stop()

    output = {
        "selected": all_data,
        "fetched_at": __import__("datetime").datetime.now().isoformat(),
    }

    with open("selected_feeds.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    total_entries = sum(len(d["feed_entries"]) for d in all_data)
    total_images = sum(
        len(e.get("downloaded_images", []))
        for d in all_data
        for e in d["feed_entries"]
    )
    total_models = sum(
        1 for d in all_data for e in d["feed_entries"] if e.get("model_file")
    )
    total_cached = sum(
        1 for d in all_data for e in d["feed_entries"] if e.get("model_file") and os.path.exists(e["model_file"])
    )
    print(f"\n{'='*50}")
    print(f"  Total entries: {total_entries}")
    print(f"  Models downloaded: {total_models}")
    print(f"  Images downloaded: {total_images}")
    print(f"  From cache: {total_cached}")
    print(f"  Saved to: selected_feeds.json")
    print(f"{'='*50}")
