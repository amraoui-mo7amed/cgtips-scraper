import argparse
import json
import logging
import os
import sys
from pathlib import Path
from tqdm import tqdm

from config import CATEGORIES_FILE, SELECTED_FEEDS_FILE, FEEDS_DIR, HEADLESS
from browser_manager import BrowserManager
from engine import (
    load_categories,
    load_cache,
    save_cache,
    sanitize,
    download_images,
)
from utils import get_feed, extract_download_url, download_from_locker

logging.basicConfig(
    level=logging.WARNING,
    format="[%(levelname)s] %(message)s",
)
for name in ("main", "utils", "scraper", "gdrive_api", "engine", "browser_manager"):
    logging.getLogger(name).setLevel(logging.INFO)
logger = logging.getLogger("main")


def run_cli():
    logger.info("=== Interactive Feed Fetcher ===")

    categories = load_categories()
    if not categories:
        logger.error("No categories found")
        sys.exit(1)

    print("\n--- Step 1: Select a category ---")
    for i, cat in enumerate(categories, 1):
        heading = cat.get("heading", {})
        print(f"  [{i}] {heading.get('name', 'Unknown')}")

    while True:
        try:
            cat_idx = int(input("\nCategory number: ").strip()) - 1
            if 0 <= cat_idx < len(categories):
                break
        except (ValueError, EOFError):
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
        except (ValueError, EOFError):
            pass

    download_choice = input("Download images from articles? (y/N): ").strip().lower()

    urls_to_fetch = []
    for idx in selected_subs:
        sub = subs[idx]
        urls_to_fetch.append(("subcategory", sub["name"], sub["feed_url"]))

    bm = BrowserManager(headless=HEADLESS)
    try:
        p_ctx, context = bm.get_context()
        page = context.pages[0] if context.pages else context.new_page()
    except Exception as e:
        logger.error("Could not initialize browser context: %s", e)
        sys.exit(1)

    cache = load_cache()
    all_data = []
    for kind, name, url in urls_to_fetch:
        print(f"\n--- {kind}: {name} ---")
        feed = get_feed(url, max_items=max_items, page=page)

        name_safe = sanitize(name)
        folder = Path(FEEDS_DIR) / cat_safe / name_safe

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

    try:
        context.close()
        p_ctx.stop()
    except Exception:
        pass

    save_cache(all_data)

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
    print(f"  Saved to: {SELECTED_FEEDS_FILE}")
    print(f"{'='*50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CGTips SketchUp Scraper")
    parser.add_argument("--web", action="store_true", help="Launch the Web UI server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the Web UI (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host for Web UI (default: 0.0.0.0)")
    args = parser.parse_args()

    if args.web:
        import uvicorn
        from config import SERVER_PORT, SERVER_HOST
        port = args.port or SERVER_PORT
        host = args.host or SERVER_HOST
        print(f"Starting CGTips Scraper Web UI on http://{host}:{port}")
        uvicorn.run("app.main:app", host=host, port=port, reload=False)
    else:
        run_cli()
