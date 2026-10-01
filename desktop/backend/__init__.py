"""
Desktop Backend package for PySide6 application.
"""
from .scraper_service import ScraperService, scraper_service
from .app_bridge import AppBridge

__all__ = ["ScraperService", "scraper_service", "AppBridge"]
