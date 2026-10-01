"""
CGTips Custom Image Provider for PySide6 / QML.
Loads remote images through the patched requests session with caching,
avoiding Qt Quick C++ network timeouts on hostile DNS routes.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, List

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import DATA_DIR, USER_AGENT

logger = logging.getLogger("image_provider")

CACHE_DIR = DATA_DIR / "cache" / "images"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=8)


class CGTipsImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # Configure high-concurrency adapter with retries
        retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._memory_cache: Dict[str, QImage] = {}
        self._max_mem_items = 150

    def requestImage(self, image_id: str, size, requested_size):
        url = urllib.parse.unquote(image_id).strip()
        if not url:
            return QImage()

        # Check in-memory cache
        if url in self._memory_cache:
            return self._memory_cache[url]

        # Check disk cache
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        cache_file = CACHE_DIR / f"{url_hash}.img"

        if cache_file.exists():
            img = QImage()
            if img.load(str(cache_file)):
                self._store_in_mem(url, img)
                return img

        # Fetch from remote
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200 and resp.content:
                img = QImage()
                if img.loadFromData(resp.content):
                    try:
                        cache_file.write_bytes(resp.content)
                    except Exception as ce:
                        logger.debug("Failed to write image cache: %s", ce)

                    self._store_in_mem(url, img)
                    return img
        except Exception as e:
            logger.warning("Failed to load image %s: %s", url, e)

        return QImage()

    def prefetch(self, urls: List[str]):
        """Prefetches a list of URLs in the background."""
        def _fetch(u: str):
            clean = u.strip()
            if not clean or not clean.startswith("http"):
                return
            h = hashlib.md5(clean.encode("utf-8")).hexdigest()
            p = CACHE_DIR / f"{h}.img"
            if p.exists():
                return
            try:
                r = self.session.get(clean, timeout=15)
                if r.status_code == 200 and r.content:
                    p.write_bytes(r.content)
            except Exception:
                pass

        for url in urls:
            _executor.submit(_fetch, url)

    def _store_in_mem(self, url: str, img: QImage):
        if len(self._memory_cache) >= self._max_mem_items:
            first_key = next(iter(self._memory_cache))
            del self._memory_cache[first_key]
        self._memory_cache[url] = img


# Global singleton instance
image_provider_instance = CGTipsImageProvider()
