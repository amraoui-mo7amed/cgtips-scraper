import logging
import json
from bs4 import BeautifulSoup as bs
from decouple import config
from playwright.sync_api import sync_playwright
from utils import get_feed

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scraper")

BASE_URL = "https://sketchup.cgtips.org"
BRAVE_PATH = config("BRAVE_PATH", default=r"C:\Users\mohamed\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe")
CHROME_PATH = config("CHROME_PATH", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class Scraper:
    def __init__(self):
        self.base_url = BASE_URL
        self.user_agent = config("USER_AGENT")
        logger.info("Scraper initialized with base_url=%s", self.base_url)

    def get_soup(self, url):
        logger.info("Fetching page: %s", url)
        try:
            with sync_playwright() as p:
                browsers_to_try = [
                    ("Brave", BRAVE_PATH),
                    ("Chrome", CHROME_PATH),
                ]
                browser = None
                last_error = None
                for name, exe_path in browsers_to_try:
                    try:
                        logger.debug("Launching %s browser (headless=False)", name)
                        browser = p.chromium.launch(executable_path=exe_path, headless=False)
                        logger.debug("%s launched successfully", name)
                        break
                    except Exception as e:
                        logger.warning("Failed to launch %s: %s", name, e)
                        last_error = e
                        continue

                if browser is None:
                    raise last_error or Exception("No browser available")

                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()
                logger.debug("Navigating to URL with 30s timeout")
                page.goto(url, timeout=30000)
                logger.info("Page loaded: %s (title: %s)", url, page.title())

                html = page.content()
                logger.debug("Page HTML captured (%d bytes)", len(html))
                browser.close()
                logger.debug("Browser closed")
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e, exc_info=True)
            return None

        soup = bs(html, "html.parser")
        logger.info("Soup parsed successfully")
        return soup

    def get_categories(self):
        logger.info("Starting category extraction from base URL")
        soup = self.get_soup(self.base_url)

        if not soup:
            logger.warning("No soup returned — skipping category extraction")
            return []

        containers = soup.find_all("div", class_="wpb_column bs-vc-column vc_column_container vc_col-sm-3")
        categories = []
        for i, container in enumerate(containers, 1):
            logger.debug("Processing container %d/%d", i, len(containers))
            entry = {}

            heading_el = container.find("h3", class_="vc_custom_heading vc_do_custom_heading")
            if heading_el:
                a_tag = heading_el.find("a")
                href = a_tag["href"] if a_tag else None
                text = heading_el.get_text(strip=True)
                if href and text:
                    entry["heading"] = {
                        "name": text,
                        "url": href,
                        "feed_url": href.rstrip("/") + "/feed",
                    }
                    logger.debug("Heading: %s (%s)", text, href)
            else:
                logger.warning("Container %d has no heading", i)

            subcategories = []
            for sub in container.find_all("li"):
                a_tag = sub.find("a")
                href = a_tag["href"] if a_tag else None
                text = a_tag.get_text(strip=True) if a_tag else None
                if href and text:
                    subcategories.append({
                        "name": text,
                        "url": href,
                        "feed_url": href.rstrip("/") + "/feed",
                    })
            entry["subcategories"] = subcategories
            logger.debug("  Subcategories: %d", len(subcategories))

            if entry.get("heading") or subcategories:
                categories.append(entry)

        logger.info("Extracted %d containers", len(categories))
        return categories
    

    def save_to_json(self, data, filename):
        logger.info("Saving data to %s (%d items)", filename, len(data))
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info("Successfully saved to %s", filename)
        except Exception as e:
            logger.error("Failed to save to %s: %s", filename, e, exc_info=True)

    


if __name__ == "__main__":
    logger.info("=== Scraper started ===")
    scraper = Scraper()

    categories = scraper.get_categories()
    if categories:
        logger.info("Categories found: %d", len(categories))
        scraper.save_to_json(categories, "categories.json")

        for cat in categories:
            heading = cat.get("heading")
            if heading:
                feed_url = heading["feed_url"]
                logger.info("Fetching feed for heading: %s (%s)", heading["name"], feed_url)
                feed = get_feed(feed_url, max_items=2)
                heading["feed_entries"] = feed

            for sub in cat.get("subcategories", []):
                feed_url = sub["feed_url"]
                logger.info("Fetching feed for subcategory: %s (%s)", sub["name"], feed_url)
                feed = get_feed(feed_url, max_items=2)
                sub["feed_entries"] = feed

        scraper.save_to_json(categories, "categories_with_feeds.json")
        logger.info("Saved categories with feeds to categories_with_feeds.json")
    else:
        logger.warning("No categories extracted")

    logger.info("=== Scraper finished ===")