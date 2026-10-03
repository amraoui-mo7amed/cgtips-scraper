"""
PySide6 QObject Bridge connecting Qt Quick (QML) directly to the in-process scraper engine.
No external REST API server required.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import (
    Property,
    QObject,
    QRunnable,
    QThread,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QFileDialog

import config
import history
from download_queue import DownloadQueue
from .library import format_bytes as _fmt_bytes

logger = logging.getLogger("app_bridge")


def _title_key(title: str) -> str:
    return history.title_key(title)


def _build_downloaded_index(library_items: List[Dict[str, Any]]) -> Dict[str, str]:
    """Maps article URLs and title keys of library items that have their model to their folder."""
    index: Dict[str, str] = {}
    for it in library_items:
        if not it.get("has_model"):
            continue
        if it.get("article_url"):
            index[it["article_url"].rstrip("/")] = it["folder_path"]
        index[_title_key(it.get("title", ""))] = it["folder_path"]
    return index


def _mark_downloaded(feed_items: List[Dict[str, Any]], index: Dict[str, str]) -> List[Dict[str, Any]]:
    out = []
    for e in feed_items:
        folder = index.get((e.get("link") or "").rstrip("/")) or index.get(_title_key(e.get("title", "")))
        downloaded = bool(folder) or history.has(e.get("link") or "", e.get("title") or "")
        out.append(dict(e, downloaded=downloaded, local_folder=folder or ""))
    return out
from .scraper_service import scraper_service


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

    feedsDirChanged = Signal()
    queueChanged = Signal()
    queueProgressChanged = Signal()
    maintenanceChanged = Signal()
    libraryImported = Signal()
    downloadJobsChanged = Signal()
    historyChanged = Signal()

    # User notification & progress signals
    toast = Signal(str, str)  # (type: 'info'|'success'|'warning'|'error', message)
    searchCompleted = Signal(bool, str)
    resolveCompleted = Signal(bool, str)
    resolverLogAdded = Signal(str)

    # Internal: lets worker threads run a callable on the GUI thread
    _runOnMain = Signal(object)

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
        self._downloaded_index: Dict[str, str] = {}  # article url / title key -> library folder
        self._library_query = ("", "all")  # last search / category the library view asked for
        self._library_loading = False
        self._library_total = 0

        self._resolver_result: Dict[str, Any] = {}
        self._is_resolving = False
        self._resolver_logs: List[str] = []

        self._maintenance_busy = False
        self._maintenance_message = ""

        # Download / import jobs shown in the header's status widget (newest first)
        self._jobs: List[Dict[str, Any]] = []
        self._job_seq = 0

        self._runOnMain.connect(self._execute_on_main)

        # Download queue (bulk downloads and "download selected" go through it)
        self._queue_items: List[Dict[str, Any]] = []
        self._queue_stats: Dict[str, Any] = {}
        self._queue_progress: Dict[str, Any] = {}
        self._queue_job_id = 0
        self._queue_user_paused = False
        self.queue = DownloadQueue(
            on_change=lambda: self._runOnMain.emit(self._refresh_queue),
            on_progress=lambda i, d, t: self._runOnMain.emit(lambda: self._queue_bytes(i, d, t)),
            on_item_done=lambda item: self._runOnMain.emit(lambda: self._add_to_library(item["folder"])),
        )
        self._refresh_queue()

    @Slot(object)
    def _execute_on_main(self, fn):
        fn()

    def _start(self, task: Callable, ok: Optional[Callable] = None, err: Optional[Callable] = None):
        """Runs task in the thread pool; ok/err callbacks run on the GUI thread."""
        self.thread_pool.start(Worker(
            task,
            on_success=(lambda r: self._runOnMain.emit(lambda: ok(r))) if ok else None,
            on_error=(lambda e: self._runOnMain.emit(lambda: err(e))) if err else None,
        ))

    # --- Properties ---

    @Property(bool, notify=isConnectedChanged)
    def isConnected(self) -> bool:
        return self._is_connected

    @Property(str, notify=feedsDirChanged)
    def feedsDir(self) -> str:
        return str(config.FEEDS_DIR)

    @Property("QVariant", notify=queueChanged)
    def queueItems(self) -> List[Dict[str, Any]]:
        return self._queue_items

    @Property("QVariant", notify=queueChanged)
    def queueStats(self) -> Dict[str, Any]:
        return self._queue_stats

    @Property("QVariant", notify=queueProgressChanged)
    def queueProgress(self) -> Dict[str, Any]:
        return self._queue_progress

    @Property(bool, notify=queueChanged)
    def isBulkRunning(self) -> bool:
        return bool(self._queue_stats.get("running"))

    @Property("QVariant", notify=downloadJobsChanged)
    def downloadJobs(self) -> List[Dict[str, Any]]:
        return self._jobs

    @Property(int, notify=historyChanged)
    def historyCount(self) -> int:
        return history.count()

    @Property(int, notify=downloadJobsChanged)
    def activeJobCount(self) -> int:
        return sum(1 for j in self._jobs if j["status"] == "running")

    # --- Download jobs ---

    def _job_add(self, kind: str, title: str, detail: str = "") -> int:
        """Registers a job (GUI thread). progress -1 means indeterminate."""
        self._job_seq += 1
        self._jobs.insert(0, {"id": self._job_seq, "kind": kind, "title": title, "detail": detail,
                              "status": "running", "progress": -1.0, "started": time.strftime("%H:%M")})
        del self._jobs[30:]
        self.downloadJobsChanged.emit()
        return self._job_seq

    def _job_update(self, job_id: int, **fields):
        """Updates a job; safe to call from worker threads."""
        def _apply():
            for i, j in enumerate(self._jobs):
                if j["id"] == job_id:
                    self._jobs[i] = dict(j, **fields)
                    self.downloadJobsChanged.emit()
                    return
        if QThread.currentThread() is self.thread():
            _apply()
        else:
            self._runOnMain.emit(_apply)

    @Slot()
    def clearFinishedJobs(self):
        self._jobs = [j for j in self._jobs if j["status"] == "running"]
        self.downloadJobsChanged.emit()

    @Property(bool, notify=maintenanceChanged)
    def maintenanceBusy(self) -> bool:
        return self._maintenance_busy

    @Property(str, notify=maintenanceChanged)
    def maintenanceMessage(self) -> str:
        return self._maintenance_message

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
            self._feed_items = _mark_downloaded(items, self._downloaded_index)
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

        slug = clean_url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        job_id = self._job_add("resolve", slug[:90] or clean_url, "Starting...")
        last_bytes = [0.0]

        def _log_cb(msg: str):
            self._resolver_logs.append(msg)
            self.resolverLogsChanged.emit()
            self.resolverLogAdded.emit(msg)
            if msg.startswith("Article title: "):
                self._job_update(job_id, title=msg[len("Article title: "):].strip("'"), detail=msg)
            else:
                self._job_update(job_id, detail=msg)

        def _progress_cb(done: int, total: int, _name: str = ""):
            if time.monotonic() - last_bytes[0] < 0.3 and done < total:
                return
            last_bytes[0] = time.monotonic()
            self._job_update(
                job_id,
                progress=(done / total) if total else -1.0,
                detail=f"Downloading model  {_fmt_bytes(done)}" + (f" / {_fmt_bytes(total)}" if total else ""),
            )

        def _task():
            return self.service.resolve_article(
                clean_url,
                download_model=download_model,
                download_images=download_images,
                log_cb=_log_cb,
                progress_cb=_progress_cb,
            )

        def _on_success(res):
            ok = bool(res.get("success")) if isinstance(res, dict) else True
            self._job_update(
                job_id, status="done" if ok else "failed", progress=1.0 if ok else -1.0,
                detail="Model and images saved" if ok else (res.get("error") or "No model downloaded"),
            )
            self._resolver_result = res
            self._is_resolving = False
            self.resolverResultChanged.emit()
            self.isResolvingChanged.emit()
            self.resolveCompleted.emit(True, "")
            self.toast.emit("success", "3D Model resolved and downloaded!")
            if isinstance(res, dict) and res.get("folder"):
                self._add_to_library(res["folder"])
            else:
                self.loadLibrary()
            self.refreshStatus()

        def _on_error(exc):
            self._job_update(job_id, status="failed", detail=str(exc)[:160])
            self._is_resolving = False
            self.isResolvingChanged.emit()
            err_msg = str(exc)
            self.resolveCompleted.emit(False, err_msg)
            self.toast.emit("error", f"Resolver error: {err_msg}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str, str)
    def loadLibrary(self, search: str = "", category: str = "all"):
        """Scans local media library and prepares file:// preview paths."""
        self._library_query = (search or "", category or "all")
        self._library_loading = True
        self.libraryLoadingChanged.emit()

        def _task():
            return self.service.get_library(search=search or None, category=category or None)

        def _on_success(res):
            items = res.get("items", [])
            if not search and (not category or category == "all"):
                self._downloaded_index = _build_downloaded_index(items)
                if self._feed_items:
                    self._feed_items = _mark_downloaded(self._feed_items, self._downloaded_index)
                    self.feedItemsChanged.emit()
            self.historyChanged.emit()
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

    def _add_to_library(self, folder: str):
        """Shows a just-downloaded article in the library without rescanning everything."""
        search, category = self._library_query
        if search or category != "all":
            self.loadLibrary(search, category)  # filtered view: let the scan decide if it belongs
            return

        def _on_success(item):
            if not item:
                return
            items = [i for i in self._library_items if i.get("folder_path") != item["folder_path"]]
            self._library_items = [item] + items
            self._library_total = len(self._library_items)
            if item.get("has_model"):
                if item.get("article_url"):
                    self._downloaded_index[item["article_url"].rstrip("/")] = item["folder_path"]
                self._downloaded_index[_title_key(item.get("title", ""))] = item["folder_path"]
                if self._feed_items:
                    self._feed_items = _mark_downloaded(self._feed_items, self._downloaded_index)
                    self.feedItemsChanged.emit()
            self.libraryItemsChanged.emit()
            self.libraryTotalChanged.emit()
            self.historyChanged.emit()

        self.thread_pool.start(Worker(lambda: self.service.library_item(folder), on_success=_on_success,
                                      on_error=lambda exc: logger.warning("Library update failed: %s", exc)))

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
        job_id = self._job_add("resolve", Path(folder_path).name[:90], "Downloading missing model...")

        def _task():
            return self.service.retry_model(folder_path)

        def _on_success(ok):
            self._job_update(job_id, status="done" if ok else "failed", progress=1.0 if ok else -1.0,
                             detail="Model downloaded" if ok else "Could not download the model (Drive link or quota)")
            if ok:
                self.toast.emit("success", "Model file re-downloaded successfully!")
                self.loadLibrary()
                self.refreshStatus()
            else:
                self.toast.emit("error", "Could not download model. Check GDrive link or quota.")

        def _on_error(exc):
            self._job_update(job_id, status="failed", detail=str(exc)[:160])
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
        target = (config.FEEDS_DIR / folder_path).resolve() if folder_path else config.FEEDS_DIR.resolve()
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

    # --- Download queue ---

    def _refresh_queue(self):
        self._queue_items = self.queue.items()
        st = self.queue.stats()
        self._queue_stats = st
        if st["current_id"] != self._queue_progress.get("id"):
            self._queue_progress = {"id": st["current_id"], "done": 0, "total": 0}
            self.queueProgressChanged.emit()
        self.queueChanged.emit()

        # One row in the header's download widget for the whole queue.
        busy = st["running"] or bool(st["listing"])
        done = st["finished"]
        title = f"Download queue  {done} / {st['total']}"
        if busy:
            if not self._queue_job_id or self._job_status(self._queue_job_id) != "running":
                self._queue_job_id = self._job_add("queue", title, "Starting...")
            self._job_update(self._queue_job_id, title=title, status="running",
                             progress=(done / st["total"]) if st["total"] else -1.0,
                             detail=st["listing"] or st["current_title"] or "")
        elif self._queue_job_id and self._job_status(self._queue_job_id) == "running":
            if st["is_paused"] and st["active"]:
                status, detail = "cancelled", f"Paused, {st['active']} waiting"
            elif st["failed"] and not st["done"]:
                status, detail = "failed", f"{st['failed']} failed"
            else:
                status, detail = "done", f"{st['done']} downloaded, {st['skipped']} skipped, {st['failed']} failed"
            self._job_update(self._queue_job_id, title=title, status=status, progress=1.0, detail=detail)

    def _job_status(self, job_id: int) -> str:
        return next((j["status"] for j in self._jobs if j["id"] == job_id), "")

    def _queue_bytes(self, item_id: int, done: int, total: int):
        self._queue_progress = {"id": item_id, "done": done, "total": total}
        self.queueProgressChanged.emit()
        if self._queue_job_id:
            title = self._queue_stats.get("current_title", "")
            size = _fmt_bytes(done) + (f" / {_fmt_bytes(total)}" if total else "")
            self._job_update(self._queue_job_id, detail=f"{title[:60]}  ({size})")

    def _check_queue_options(self, download_model: bool, download_images: bool) -> bool:
        if not (download_model or download_images):
            self.toast.emit("warning", "Enable at least Models or Images")
            return False
        return True

    @Slot("QVariantList", int, bool, bool)
    def startBulkSubcategories(self, subcategories, max_items: int = 0, download_model: bool = True, download_images: bool = True):
        """subcategories: [{category, subcategory, feed_url}, ...]. max_items 0 = whole feed."""
        groups = [
            {"category": g.get("category", ""), "subcategory": g.get("subcategory", ""), "feed_url": g.get("feed_url", "")}
            for g in subcategories if g.get("feed_url")
        ]
        if not groups:
            self.toast.emit("warning", "Nothing selected to download")
            return
        if not self._check_queue_options(download_model, download_images):
            return

        def _done(n: int):
            msg = f"Added {n} articles to the download queue" if n else "Nothing new to add to the queue"
            if n and self._queue_user_paused:
                msg += " (the queue is paused)"
            self._runOnMain.emit(lambda: self.toast.emit("success" if n else "info", msg))

        self.queue.add_feeds(groups, max_items, download_model, download_images,
                             start=not self._queue_user_paused, done_cb=_done)
        plural = "s" if len(groups) != 1 else ""
        self.toast.emit("info", f"Reading {len(groups)} feed{plural} into the download queue...")

    @Slot(str, str, "QVariantList", bool, bool)
    def startBulkArticles(self, category: str, subcategory: str, articles, download_model: bool = True, download_images: bool = True):
        """articles: [{title, link}, ...] picked from one feed."""
        if not self._check_queue_options(download_model, download_images):
            return
        items = [{"title": a.get("title", ""), "link": a.get("link", "")} for a in articles if a.get("link")]
        n = self.queue.add_articles(items, category, subcategory, download_model, download_images,
                                    start=not self._queue_user_paused)
        self.toast.emit("success" if n else "info",
                        f"Added {n} articles to the download queue" if n else "Those articles are already queued")

    @Slot()
    def queuePause(self):
        self._queue_user_paused = True
        self.queue.pause()

    @Slot()
    def queueResume(self):
        self._queue_user_paused = False
        self.queue.resume()

    @Slot(int)
    def queueRetry(self, item_id: int):
        self._queue_user_paused = False
        self.queue.retry(item_id)

    @Slot()
    def queueRetryFailed(self):
        self._queue_user_paused = False
        n = self.queue.retry_failed()
        self.toast.emit("info" if n else "warning", f"Retrying {n} failed downloads" if n else "No failed downloads")

    @Slot(int)
    def queueRemove(self, item_id: int):
        self.queue.remove(item_id)

    @Slot(int)
    def queueMoveToTop(self, item_id: int):
        self.queue.move_to_top(item_id)

    @Slot()
    def queueClearFinished(self):
        self.queue.clear_finished()

    def _set_busy(self, busy: bool, message: str = ""):
        self._maintenance_busy = busy
        self._maintenance_message = message
        self.maintenanceChanged.emit()

    def _run_maintenance(self, message: str, task: Callable, on_done: Callable[[Any], str]):
        if self._maintenance_busy:
            self.toast.emit("warning", "Another operation is still running")
            return
        self._set_busy(True, message)

        def _ok(res):
            self._set_busy(False)
            self.toast.emit("success", on_done(res))

        def _err(exc):
            self._set_busy(False)
            self.toast.emit("error", str(exc))

        self._start(task, _ok, _err)

    @Slot(bool)
    def chooseStorageDir(self, move_existing: bool = False):
        """Lets the user pick a new download/library directory."""
        start = str(config.FEEDS_DIR)
        chosen = QFileDialog.getExistingDirectory(None, "Choose storage directory", start)
        if not chosen:
            return

        def _task():
            return self.service.set_storage_dir(chosen, move_existing=move_existing)

        def _done(res):
            self.feedsDirChanged.emit()
            self.loadLibrary()
            self.refreshStatus()
            extra = f" ({res['moved']} items moved" + (f", {res['conflicts']} conflicts left in place" if res["conflicts"] else "") + ")" if move_existing else ""
            return f"Storage location set to {res['feeds_dir']}{extra}"

        self._run_maintenance("Changing storage location...", _task, _done)

    @Slot(bool)
    def exportCache(self, include_images: bool = True):
        name = f"cgtips-cache-{time.strftime('%Y%m%d')}.zip"
        path, _ = QFileDialog.getSaveFileName(None, "Export cache", str(Path.home() / name), "Cache archive (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"

        self._run_maintenance(
            "Exporting cache...",
            lambda: self.service.export_cache(path, include_images=include_images),
            lambda r: f"Cache exported: {len(r['json_files'])} data files, {r['images']} thumbnails",
        )

    @Slot()
    def importCache(self):
        path, _ = QFileDialog.getOpenFileName(None, "Import cache", str(Path.home()), "Cache archive (*.zip)")
        if not path:
            return

        def _done(r):
            self.loadCategories()
            self.refreshStatus()
            return f"Cache imported: {len(r['json_files'])} data files, {r['images_added']} new thumbnails"

        self._run_maintenance("Importing cache...", lambda: self.service.import_cache(path), _done)

    def _import_library(self, paths: List[str], move: bool):
        if self._maintenance_busy:
            self.toast.emit("warning", "Another operation is still running")
            return
        job_id = self._job_add("import", "Import into library", "Scanning folders...")

        def _progress(idx: int, total: int):
            self._job_update(job_id, progress=idx / total if total else -1.0, detail=f"{idx} / {total} items")

        def _done(r):
            self.loadLibrary()
            self.refreshStatus()
            self.libraryImported.emit()
            msg = f"Imported {r['imported']} of {r['found']} items ({r['skipped']} already present"
            msg += f", {r['failed']} failed: {'; '.join(r['errors'][:2])})" if r["failed"] else ")"
            if r["found"] == 0 and r["notes"]:
                msg = r["notes"][0]
            failed_all = r["failed"] and not r["imported"]
            self._job_update(job_id, status="failed" if failed_all else "done", progress=1.0, detail=msg)
            return msg

        def _task():
            try:
                return self.service.import_library(paths, move=move, progress_cb=_progress)
            except Exception as e:
                self._job_update(job_id, status="failed", detail=str(e)[:220])
                raise

        self._run_maintenance("Importing downloads into the library...", _task, _done)

    @Slot()
    def importHistory(self):
        """Merges a download history (or an old selected_feeds.json) so those articles aren't downloaded again."""
        path, _ = QFileDialog.getOpenFileName(
            None, "Import download history", str(Path.home()),
            "Download history or feeds file (*.json)",
        )
        if not path:
            return

        def _done(r):
            self.historyChanged.emit()
            self.loadLibrary()
            return (f"Download history: {r['added']} new articles added ({r['downloaded']} of {r['found']} "
                    f"in the file were downloaded). {r['total']} articles will be skipped.")

        self._run_maintenance("Importing download history...", lambda: self.service.import_history(path), _done)

    @Slot()
    def exportHistory(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "Export download history", str(Path.home() / "download_history.json"), "Download history (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._run_maintenance("Exporting download history...", lambda: self.service.export_history(path),
                              lambda n: f"Download history exported: {n} articles")

    @Slot(bool)
    def importLibraryFolder(self, move: bool = False):
        """Imports a folder of previously downloaded models (any depth)."""
        chosen = QFileDialog.getExistingDirectory(None, "Choose a folder with downloaded models", str(Path.home()))
        if chosen:
            self._import_library([chosen], move)

    @Slot(bool)
    def importLibraryFiles(self, move: bool = False):
        """Imports individually selected model archives / images."""
        files, _ = QFileDialog.getOpenFileNames(
            None, "Choose model archives / images", str(Path.home()),
            "Models & images (*.zip *.rar *.7z *.skp *.jpg *.jpeg *.png *.webp)",
        )
        if files:
            self._import_library(files, move)
