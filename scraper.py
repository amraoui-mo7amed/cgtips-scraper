import logging
import json
from bs4 import BeautifulSoup as bs
from decouple import config
from browser_manager import BrowserManager
from config import BASE_URL, USER_AGENT, HEADLESS, CATEGORIES_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scraper")


class Scraper:
    def __init__(self, headless=None, user_agent=None):
        self.base_url = BASE_URL
        self.user_agent = user_agent or USER_AGENT
        self.headless = HEADLESS if headless is None else headless
        self.browser_manager = BrowserManager(headless=self.headless, user_agent=self.user_agent)
        logger.info("Scraper initialized with base_url=%s, headless=%s", self.base_url, self.headless)

    def get_soup(self, url):
        """Fetches page HTML using fast requests first, cloudscraper second, and Playwright fallback."""
        logger.info("Fetching page: %s", url)
        # 1. Fast requests attempt
        try:
            import requests
            r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            if r.status_code == 200 and len(r.text) > 1000:
                logger.debug("Fast requests fetch succeeded (%d bytes)", len(r.content))
                return bs(r.content, "html.parser")
        except Exception as e:
            logger.debug("Fast requests failed (%s), trying cloudscraper", e)

        # 2. Cloudscraper attempt
        try:
            import cloudscraper
            s = cloudscraper.create_scraper()
            s.headers.update({"User-Agent": self.user_agent})
            r = s.get(url, timeout=15)
            if r.status_code == 200 and len(r.text) > 1000:
                logger.debug("Cloudscraper fetch succeeded (%d bytes)", len(r.content))
                return bs(r.content, "html.parser")
        except Exception as e:
            logger.debug("Cloudscraper failed (%s), falling back to browser", e)

        # 2. Playwright fallback
        try:
            p, context = self.browser_manager.get_context()
            page = context.new_page()
            logger.debug("Navigating with Playwright (30s timeout)")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            html = page.content()
            context.close()
            p.stop()
            logger.debug("Browser page HTML captured (%d bytes)", len(html))
            return bs(html, "html.parser")
        except Exception as e:
            logger.error("Failed to fetch %s via browser: %s", url, e, exc_info=True)
            return None

    def get_categories(self):
        logger.info("Starting category extraction from base URL: %s", self.base_url)
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

        logger.info("Extracted %d categories from site", len(categories))
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
        scraper.save_to_json(categories, str(CATEGORIES_FILE))
        print(f"Extracted and saved {len(categories)} categories to {CATEGORIES_FILE}")
    else:
        print("No categories extracted.")