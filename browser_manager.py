import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Playwright

from config import USER_AGENT, HEADLESS, BRAVE_PATH, CHROME_PATH, DATA_DIR

logger = logging.getLogger("browser_manager")


class BrowserManager:
    def __init__(self, headless: Optional[bool] = None, user_agent: Optional[str] = None):
        self.headless = HEADLESS if headless is None else headless
        self.user_agent = user_agent or USER_AGENT
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def _get_candidate_executables(self):
        candidates = []
        # Check custom Brave path if provided and exists
        if BRAVE_PATH and os.path.isfile(BRAVE_PATH):
            candidates.append(("Brave (custom)", BRAVE_PATH))

        # Check custom Chrome path if provided and exists
        if CHROME_PATH and os.path.isfile(CHROME_PATH):
            candidates.append(("Chrome (custom)", CHROME_PATH))

        # Platform-specific standard locations (optional checks)
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
            win_brave = os.path.join(local_appdata, r"BraveSoftware\Brave-Browser\Application\brave.exe")
            win_chrome = os.path.join(prog_files, r"Google\Chrome\Application\chrome.exe")
            if os.path.isfile(win_brave):
                candidates.append(("Brave (Windows)", win_brave))
            if os.path.isfile(win_chrome):
                candidates.append(("Chrome (Windows)", win_chrome))

        return candidates

    def get_context(self) -> Tuple[Playwright, BrowserContext]:
        """
        Launches browser and returns (playwright_instance, context).
        Prioritizes Playwright Chromium for maximum reliability across Docker, Linux, macOS, and Windows,
        or falls back to custom browser paths if configured.
        """
        p = sync_playwright().start()
        context = None

        # 1. Try launching standard Playwright Chromium first (ideal for Docker & general use)
        try:
            logger.debug("Launching Playwright built-in Chromium (headless=%s)", self.headless)
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--host-resolver-rules=MAP sketchup.cgtips.org 104.21.74.130, MAP cgtips.org 104.21.74.130, MAP www.cgtips.org 104.21.74.130",
                ],
            )
            context = browser.new_context(
                user_agent=self.user_agent,
                accept_downloads=True,
            )
            logger.info("Playwright Chromium browser launched successfully")
            return p, context
        except Exception as e:
            logger.warning("Default Playwright Chromium launch failed: %s. Trying candidate executables...", e)

        # 2. Try candidate custom executables if any exist
        for name, exe_path in self._get_candidate_executables():
            try:
                logger.debug("Attempting to launch %s from %s", name, exe_path)
                browser = p.chromium.launch(
                    executable_path=exe_path,
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--host-resolver-rules=MAP sketchup.cgtips.org 104.21.74.130, MAP cgtips.org 104.21.74.130, MAP www.cgtips.org 104.21.74.130",
                    ],
                )
                context = browser.new_context(
                    user_agent=self.user_agent,
                    accept_downloads=True,
                )
                logger.info("Launched %s successfully", name)
                return p, context
            except Exception as exe_err:
                logger.warning("Failed launching %s: %s", name, exe_err)

        p.stop()
        raise RuntimeError("No available browser could be launched. Please ensure Playwright chromium is installed.")


def get_browser_context(headless: Optional[bool] = None, user_agent: Optional[str] = None):
    bm = BrowserManager(headless=headless, user_agent=user_agent)
    return bm.get_context()
