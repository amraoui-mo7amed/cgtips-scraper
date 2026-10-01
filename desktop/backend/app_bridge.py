"""
PySide6 QObject Bridge connecting Qt Quick (QML) directly to the in-process scraper engine.
No external REST API server required.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import (
    Property,
    QObject,
    QRunnable,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication

from .scraper_service import scraper_service, FEEDS_DIR


class Worker(QRunnable):
    """Generic worker for running scraper operations in background threads."""

    def __init__(
        self,
        fn: Callable,
        *args,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.on_success = on_success
        self.on_error = on_error

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            if self.on_success:
                self.on_success(result)
        except Exception as exc:
            if self.on_error:
                self.on_error(exc)


class AppBridge(QObject):
    # Reactive state change signals
    statusDataChanged = Signal()
    isConnectedChanged = Signal()

    searchResultsChanged = Signal()
    isSearchingChanged = Signal()
    searchQueryChanged = Signal()

    categoriesChanged = Signal()
    categoriesLoadingChanged = Signal()

    feedItemsChanged = Signal()
    feedLoadingChanged = Signal()

    libraryItemsChanged = Signal()
    libraryLoadingChanged = Signal()
    libraryTotalChanged = Signal()

    resolverResultChanged = Signal()
    isResolvingChanged = Signal()
    resolverLogsChanged = Signal()

    # User notification & progress signals
    toast = Signal(str, str)  # (type: 'info'|'success'|'warning'|'error', message)
    searchCompleted = Signal(bool, str)
    resolveCompleted = Signal(bool, str)
    resolverLogAdded = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.thread_pool = QThreadPool.globalInstance()
        self.service = scraper_service

        self._is_connected = True  # Always online in direct scraper mode
        self._status_data: Dict[str, Any] = {}

        self._search_results: List[Dict[str, Any]] = []
        self._is_searching = False
        self._search_query = ""

        self._categories: List[Dict[str, Any]] = []
        self._categories_loading = False

        self._feed_items: List[Dict[str, Any]] = []
        self._feed_loading = False

        self._library_items: List[Dict[str, Any]] = []
        self._library_loading = False
        self._library_total = 0

        self._resolver_result: Dict[str, Any] = {}
        self._is_resolving = False
        self._resolver_logs: List[str] = []

    # --- Properties ---

    @Property(bool, notify=isConnectedChanged)
    def isConnected(self) -> bool:
        return self._is_connected

    @Property(str, constant=True)
    def feedsDir(self) -> str:
        return str(FEEDS_DIR)

    @Property("QVariant", notify=statusDataChanged)
    def statusData(self) -> Dict[str, Any]:
        return self._status_data

    @Property("QVariant", notify=searchResultsChanged)
    def searchResults(self) -> List[Dict[str, Any]]:
        return self._search_results

    @Property(bool, notify=isSearchingChanged)
    def isSearching(self) -> bool:
        return self._is_searching

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property("QVariant", notify=categoriesChanged)
    def categories(self) -> List[Dict[str, Any]]:
        return self._categories

    @Property(bool, notify=categoriesLoadingChanged)
    def categoriesLoading(self) -> bool:
        return self._categories_loading

    @Property("QVariant", notify=feedItemsChanged)
    def feedItems(self) -> List[Dict[str, Any]]:
        return self._feed_items

    @Property(bool, notify=feedLoadingChanged)
    def feedLoading(self) -> bool:
        return self._feed_loading

    @Property("QVariant", notify=libraryItemsChanged)
    def libraryItems(self) -> List[Dict[str, Any]]:
        return self._library_items

    @Property(bool, notify=libraryLoadingChanged)
    def libraryLoading(self) -> bool:
        return self._library_loading

    @Property(int, notify=libraryTotalChanged)
    def libraryTotal(self) -> int:
        return self._library_total

    @Property("QVariant", notify=resolverResultChanged)
    def resolverResult(self) -> Dict[str, Any]:
        return self._resolver_result

    @Property(bool, notify=isResolvingChanged)
    def isResolving(self) -> bool:
        return self._is_resolving

    @Property("QVariant", notify=resolverLogsChanged)
    def resolverLogs(self) -> List[str]:
        return self._resolver_logs

    # --- Slots & Methods ---

    @Slot()
    def refreshStatus(self):
        """Fetches direct scraper status and disk metrics in background."""
        def _task():
            return self.service.get_system_status()

        def _on_success(data):
            self._status_data = data
            self.statusDataChanged.emit()

        self.thread_pool.start(Worker(_task, on_success=_on_success))

    @Slot(str, int)
    def performSearch(self, query: str, page: int = 1):
        """Directly queries CGTips site for models matching the keyword."""
        q = query.strip()
        if not q:
            return

        self._is_searching = True
        self._search_query = q
        self.isSearchingChanged.emit()
        self.searchQueryChanged.emit()

        def _task():
            return self.service.search(q, page=page)

        def _on_success(results):
            self._search_results = results
            self._is_searching = False
            self.searchResultsChanged.emit()
            self.isSearchingChanged.emit()
            self.searchCompleted.emit(True, "")

        def _on_error(exc):
            self._is_searching = False
            self.isSearchingChanged.emit()
            self.searchCompleted.emit(False, str(exc))
            self.toast.emit("error", f"Search error: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot()
    def clearSearch(self):
        self._search_results = []
        self._search_query = ""
        self.searchResultsChanged.emit()
        self.searchQueryChanged.emit()

    @Slot(bool)
    def loadCategories(self, refresh: bool = False):
        """Loads categories hierarchy from cache or directly scrapes site."""
        self._categories_loading = True
        self.categoriesLoadingChanged.emit()

        def _task():
            return self.service.get_categories(refresh=refresh)

        def _on_success(cats):
            self._categories = cats
            self._categories_loading = False
            self.categoriesChanged.emit()
            self.categoriesLoadingChanged.emit()
            if refresh:
                self.toast.emit("success", "Categories refreshed from site!")

        def _on_error(exc):
            self._categories_loading = False
            self.categoriesLoadingChanged.emit()
            self.toast.emit("error", f"Categories load failed: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def previewFeed(self, feed_url: str):
        """Fetches RSS feed preview entries directly."""
        self._feed_loading = True
        self._feed_items = []
        self.feedLoadingChanged.emit()
        self.feedItemsChanged.emit()

        def _task():
            return self.service.get_feed_preview(feed_url, limit=15)

        def _on_success(items):
            self._feed_items = items
            self._feed_loading = False
            self.feedItemsChanged.emit()
            self.feedLoadingChanged.emit()

        def _on_error(exc):
            self._feed_loading = False
            self.feedLoadingChanged.emit()
            self.toast.emit("error", f"Feed preview failed: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str, bool, bool)
    def resolveArticle(self, url: str, download_model: bool = True, download_images: bool = True):
        """Bypasses content locker and downloads model + images directly."""
        clean_url = url.strip()
        if not clean_url:
            self.toast.emit("warning", "Please provide a valid article URL")
            return

        self._is_resolving = True
        self._resolver_result = {}
        self._resolver_logs = []
        self.resolverResultChanged.emit()
        self.isResolvingChanged.emit()
        self.resolverLogsChanged.emit()

        def _log_cb(msg: str):
            self._resolver_logs.append(msg)
            self.resolverLogsChanged.emit()
            self.resolverLogAdded.emit(msg)

        def _task():
            return self.service.resolve_article(
                clean_url,
                download_model=download_model,
                download_images=download_images,
                log_cb=_log_cb,
            )

        def _on_success(res):
            self._resolver_result = res
            self._is_resolving = False
            self.resolverResultChanged.emit()
            self.isResolvingChanged.emit()
            self.resolveCompleted.emit(True, "")
            self.toast.emit("success", "3D Model resolved and downloaded!")
            self.loadLibrary()
            self.refreshStatus()

        def _on_error(exc):
            self._is_resolving = False
            self.isResolvingChanged.emit()
            err_msg = str(exc)
            self.resolveCompleted.emit(False, err_msg)
            self.toast.emit("error", f"Resolver error: {err_msg}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str, str)
    def loadLibrary(self, search: str = "", category: str = "all"):
        """Scans local media library and prepares file:// preview paths."""
        self._library_loading = True
        self.libraryLoadingChanged.emit()

        def _task():
            return self.service.get_library(search=search or None, category=category or None)

        def _on_success(res):
            items = res.get("items", [])
            self._library_items = items
            self._library_total = res.get("total", len(items))
            self._library_loading = False
            self.libraryItemsChanged.emit()
            self.libraryTotalChanged.emit()
            self.libraryLoadingChanged.emit()

        def _on_error(exc):
            self._library_loading = False
            self.libraryLoadingChanged.emit()
            self.toast.emit("error", f"Library load failed: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def deleteLibraryModel(self, folder_path: str):
        """Deletes model folder from local library."""
        def _task():
            return self.service.delete_model(folder_path)

        def _on_success(ok):
            if ok:
                self.toast.emit("success", "Model folder deleted from disk")
                self.loadLibrary()
                self.refreshStatus()
            else:
                self.toast.emit("error", "Could not delete model folder")

        def _on_error(exc):
            self.toast.emit("error", f"Delete error: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def retryLibraryModel(self, folder_path: str):
        """Retries downloading missing model archive."""
        self.toast.emit("info", f"Retrying model download for {folder_path}...")

        def _task():
            return self.service.retry_model(folder_path)

        def _on_success(ok):
            if ok:
                self.toast.emit("success", "Model file re-downloaded successfully!")
                self.loadLibrary()
                self.refreshStatus()
            else:
                self.toast.emit("error", "Could not download model. Check GDrive link or quota.")

        def _on_error(exc):
            self.toast.emit("error", f"Retry error: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def clearCache(self, target: str):
        """Clears local cache files."""
        def _task():
            return self.service.clear_cache(target)

        def _on_success(cleared):
            self.toast.emit("success", f"Cache cleared: {', '.join(cleared) if cleared else 'None'}")
            self.loadCategories()
            self.refreshStatus()

        def _on_error(exc):
            self.toast.emit("error", f"Clear cache failed: {str(exc)}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def openFolder(self, folder_path: str):
        """Opens folder in macOS Finder / system file manager."""
        target = (FEEDS_DIR / folder_path).resolve() if folder_path else FEEDS_DIR.resolve()
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)

        if sys.platform == "darwin":
            subprocess.run(["open", str(target)], check=False)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    @Slot(str)
    def openLocalFolder(self, folder_path: str):
        """Alias for openFolder."""
        self.openFolder(folder_path)

    @Slot(str)
    def openWeb(self, url: str):
        """Opens URL in external default browser."""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(str)
    def openExternalUrl(self, url: str):
        """Alias for openWeb."""
        self.openWeb(url)

    @Slot(str)
    def copyToClipboard(self, text: str):
        """Copies text to system clipboard and shows a toast notification."""
        clean_text = str(text or "").strip()
        if not clean_text:
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_text)
            self.toast.emit("success", "Link copied to clipboard!")

