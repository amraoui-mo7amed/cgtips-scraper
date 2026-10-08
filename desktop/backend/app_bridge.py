"""
PySide6 QObject Bridge connecting Qt Quick (QML) directly to the in-process scraper engine.
Provides reactive properties, background threading, native dialogs, batch downloads,
multi-destination disk copying, and library management.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
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
from PySide6.QtWidgets import QFileDialog

import config
import history
from download_queue import DownloadQueue
from .library import format_bytes as _fmt_bytes
from .scraper_service import scraper_service, FEEDS_DIR
from .settings_manager import settings_manager
from .library import library_manager

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
                try:
                    self.on_success(result)
                except RuntimeError as re:
                    if "deleted" in str(re).lower():
                        return
                    raise
        except RuntimeError as re:
            if "deleted" in str(re).lower():
                return
            if self.on_error:
                try:
                    self.on_error(re)
                except RuntimeError:
                    pass
        except Exception as exc:
            if self.on_error:
                try:
                    self.on_error(exc)
                except RuntimeError:
                    pass


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
    missingModelsCountChanged = Signal()
    subcategoriesHierarchyChanged = Signal()

    resolverResultChanged = Signal()
    isResolvingChanged = Signal()
    resolverLogsChanged = Signal()

    # Settings signals
    clientAgentPathChanged = Signal()
    copyDestinationsChanged = Signal()

    # Batch download signals
    batchDownloadingChanged = Signal()
    batchDownloadProgressChanged = Signal()
    batchDownloadLogsChanged = Signal()
    batchDownloadLogAdded = Signal(str)
    batchDownloadFinished = Signal(int, int, int)  # (succeeded, failed, total)
    autoRetryEnabledChanged = Signal()

    # Multi-disk copy signals
    isCopyingChanged = Signal()
    copyProgressChanged = Signal()
    copyLogsChanged = Signal()
    copyLogAdded = Signal(str)
    copyFinished = Signal(bool, str)  # (success, message)

    # Loft Design API signals
    apiUrlChanged = Signal()
    apiUsernameChanged = Signal()
    apiPasswordChanged = Signal()
    apiConnectionTested = Signal(bool, str)

    # Article upload signals
    isUploadingChanged = Signal()
    uploadProgressChanged = Signal()
    uploadLogsChanged = Signal()
    uploadLogAdded = Signal(str)
    uploadFinished = Signal(int, int, int)  # (succeeded, failed, total)

    # User notification & progress signals
    toast = Signal(str, str)  # (type: 'info'|'success'|'warning'|'error', message)
    searchCompleted = Signal(bool, str)
    resolveCompleted = Signal(bool, str)
    resolverLogAdded = Signal(str)

    # Queue, history & storage signals
    feedsDirChanged = Signal()
    queueChanged = Signal()
    queueProgressChanged = Signal()
    maintenanceChanged = Signal()
    libraryImported = Signal()
    downloadJobsChanged = Signal()
    historyChanged = Signal()
    _runOnMain = Signal(object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.thread_pool = QThreadPool.globalInstance()
        self.service = scraper_service

        self._is_connected = True
        self._status_data: Dict[str, Any] = {}

        self._search_results: List[Dict[str, Any]] = []
        self._is_searching = False
        self._search_query = ""

        self._categories: List[Dict[str, Any]] = []
        self._categories_loading = False

        self._feed_items: List[Dict[str, Any]] = []
        self._feed_loading = False

        self._library_items: List[Dict[str, Any]] = []
        self._downloaded_index: Dict[str, str] = {}
        self._library_query = ("", "all")
        self._library_loading = False
        self._library_total = 0
        self._missing_models_count = 0
        self._subcategories_hierarchy: Dict[str, Any] = {}

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

        # Batch downloader state
        self._is_batch_downloading = False
        self._batch_progress: Dict[str, Any] = {
            "current": 0,
            "total": 0,
            "title": "",
            "status": "",
            "percent": 0.0,
        }
        self._batch_logs: List[str] = []
        self._batch_stop_event = threading.Event()
        self._auto_retry_enabled = False

        # Copy state
        self._is_copying = False
        self._copy_progress: Dict[str, Any] = {
            "current": 0,
            "total": 0,
            "title": "",
            "currentDest": "",
            "percent": 0.0,
            "bytesText": "0 B",
        }
        self._copy_logs: List[str] = []
        self._copy_stop_event = threading.Event()

        # Upload state
        self._is_uploading = False
        self._upload_progress: Dict[str, Any] = {
            "current": 0,
            "total": 0,
            "title": "",
            "status": "",
            "percent": 0.0,
        }
        self._upload_logs: List[str] = []
        self._upload_stop_event = threading.Event()

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

    @Property("QVariant", notify=categoriesChanged)
    def categoryNames(self) -> List[str]:
        """Returns ordered list of all category names from site and library."""
        names: List[str] = []
        for cat in self._categories:
            cname = cat.get("title") or cat.get("name")
            if cname and cname not in names:
                names.append(cname)
        for cat in self._subcategories_hierarchy.keys():
            if cat not in names:
                names.append(cat)
        return names

    @Property("QVariant", notify=categoriesChanged)
    def categorySubcategoriesMap(self) -> Dict[str, List[str]]:
        """Returns mapping of category name to list of its subcategories."""
        mapping: Dict[str, List[str]] = {}
        for cat in self._categories:
            cname = cat.get("title") or cat.get("name")
            if not cname:
                continue
            subs = [
                s.get("title") or s.get("name")
                for s in cat.get("subcategories", [])
                if (s.get("title") or s.get("name"))
            ]
            mapping[cname] = subs

        for cat, subs in self._subcategories_hierarchy.items():
            if cat not in mapping:
                mapping[cat] = list(subs)
            else:
                for s in subs:
                    if s not in mapping[cat]:
                        mapping[cat].append(s)
        return mapping

    @Slot(str, result="QVariant")
    def getSubcategoriesForCategory(self, category_name: str) -> List[str]:
        mapping = self.categorySubcategoriesMap
        return mapping.get(str(category_name).strip(), [])

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

    @Property(int, notify=missingModelsCountChanged)
    def missingModelsCount(self) -> int:
        return self._missing_models_count

    @Property("QVariant", notify=subcategoriesHierarchyChanged)
    def subcategoriesHierarchy(self) -> Dict[str, Any]:
        return self._subcategories_hierarchy

    @Property("QVariant", notify=resolverResultChanged)
    def resolverResult(self) -> Dict[str, Any]:
        return self._resolver_result

    @Property(bool, notify=isResolvingChanged)
    def isResolving(self) -> bool:
        return self._is_resolving

    @Property("QVariant", notify=resolverLogsChanged)
    def resolverLogs(self) -> List[str]:
        return self._resolver_logs

    # Settings Properties
    @Property(str, notify=clientAgentPathChanged)
    def clientAgentPath(self) -> str:
        return settings_manager.get_client_agent_path()

    @Property("QVariant", notify=copyDestinationsChanged)
    def copyDestinations(self) -> List[str]:
        return settings_manager.get_copy_destinations()

    # Batch Downloader Properties
    @Property(bool, notify=batchDownloadingChanged)
    def isBatchDownloading(self) -> bool:
        return self._is_batch_downloading

    @Property("QVariant", notify=batchDownloadProgressChanged)
    def batchDownloadProgress(self) -> Dict[str, Any]:
        return self._batch_progress

    @Property("QVariant", notify=batchDownloadLogsChanged)
    def batchDownloadLogs(self) -> List[str]:
        return self._batch_logs

    @Property(bool, notify=autoRetryEnabledChanged)
    def autoRetryEnabled(self) -> bool:
        return self._auto_retry_enabled

    # Multi-Disk Copy Properties
    @Property(bool, notify=isCopyingChanged)
    def isCopying(self) -> bool:
        return self._is_copying

    @Property("QVariant", notify=copyProgressChanged)
    def copyProgress(self) -> Dict[str, Any]:
        return self._copy_progress

    @Property("QVariant", notify=copyLogsChanged)
    def copyLogs(self) -> List[str]:
        return self._copy_logs

    # Loft Design API Properties
    @Property(str, notify=apiUrlChanged)
    def apiUrl(self) -> str:
        return settings_manager.get_api_url()

    @Property(str, notify=apiUsernameChanged)
    def apiUsername(self) -> str:
        return settings_manager.get_api_username()

    @Property(str, notify=apiPasswordChanged)
    def apiPassword(self) -> str:
        return settings_manager.get_api_password()

    # Article Upload Properties
    @Property(bool, notify=isUploadingChanged)
    def isUploading(self) -> bool:
        return self._is_uploading

    @Property("QVariant", notify=uploadProgressChanged)
    def uploadProgress(self) -> Dict[str, Any]:
        return self._upload_progress

    @Property("QVariant", notify=uploadLogsChanged)
    def uploadLogs(self) -> List[str]:
        return self._upload_logs

    # --- Slots & Methods ---

    # Settings & Destination Disks Slots
    @Slot()
    def selectClientAgentFile(self):
        """Native file picker for choosing client agent executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Client Agent Executable",
            "",
            "Executable Files (*.exe *.bin *; All Files (*)",
        )
        if file_path:
            settings_manager.set_client_agent_path(file_path)
            self.clientAgentPathChanged.emit()
            self.toast.emit("success", f"Client Agent set to: {Path(file_path).name}")

    @Slot(str)
    def setClientAgentPath(self, path: str):
        settings_manager.set_client_agent_path(path)
        self.clientAgentPathChanged.emit()

    @Slot()
    def clearClientAgentFile(self):
        settings_manager.set_client_agent_path("")
        self.clientAgentPathChanged.emit()
        self.toast.emit("info", "Client Agent configuration cleared")

    @Slot()
    def addCopyDestination(self):
        """Native directory picker for selecting a destination disk or folder."""
        folder_path = QFileDialog.getExistingDirectory(
            None, "Select Destination Disk or Directory"
        )
        if folder_path:
            if settings_manager.add_copy_destination(folder_path):
                self.copyDestinationsChanged.emit()
                self.toast.emit("success", f"Added destination disk: {folder_path}")
            else:
                self.toast.emit("info", "Destination is already in the list")

    @Slot(str)
    def removeCopyDestination(self, path: str):
        if settings_manager.remove_copy_destination(path):
            self.copyDestinationsChanged.emit()
            self.toast.emit("info", f"Removed destination: {path}")

    @Slot()
    def clearCopyDestinations(self):
        settings_manager.clear_copy_destinations()
        self.copyDestinationsChanged.emit()
        self.toast.emit("info", "Cleared all destination disks")

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

        job_id = self._job_add("resolve", clean_url[:90], "Connecting...")

        def _log_cb(msg: str):
            self._resolver_logs.append(msg)
            self.resolverLogsChanged.emit()
            self.resolverLogAdded.emit(msg)

        def _progress_cb(done: int, total: int, _name: str = ""):
            if total > 0:
                self._job_update(job_id, progress=done / total, detail=f"{_fmt_bytes(done)} / {_fmt_bytes(total)}")
            else:
                self._job_update(job_id, detail=_fmt_bytes(done))

        def _task():
            return self.service.resolve_article(
                clean_url,
                download_model=download_model,
                download_images=download_images,
                log_cb=_log_cb,
                progress_cb=_progress_cb,
            )

        def _on_success(res):
            self._job_update(job_id, status="done", progress=1.0, detail="Completed")
            self._resolver_result = res
            self._is_resolving = False
            self.resolverResultChanged.emit()
            self.isResolvingChanged.emit()
            self.resolveCompleted.emit(True, "")
            self.toast.emit("success", "3D Model resolved and downloaded!")
            if res.get("folder"):
                self._add_to_library(res["folder"])
            self.loadLibrary()
            self.refreshStatus()

        def _on_error(exc):
            err_msg = str(exc)
            self._job_update(job_id, status="failed", detail=err_msg[:160])
            self._is_resolving = False
            self.isResolvingChanged.emit()
            self.resolveCompleted.emit(False, err_msg)
            self.toast.emit("error", f"Resolver error: {err_msg}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot()
    @Slot(str)
    @Slot(str, str)
    @Slot(str, str, bool)
    def loadLibrary(self, search: str = "", category: str = "all", missing_only: bool = False):
        """Scans local media library and prepares file:// preview paths."""
        self._library_query = (search, category)
        self._library_loading = True
        self.libraryLoadingChanged.emit()

        def _task():
            return self.service.get_library(
                search=search or None,
                category=category or None,
                missing_only=missing_only,
            )

        def _on_success(res):
            items = res.get("items", [])
            stats = res.get("stats", {})
            self._library_items = items
            self._library_total = stats.get("total_models", len(items))
            self._missing_models_count = stats.get("missing_models", 0)
            self._subcategories_hierarchy = library_manager.scan_library().get("subcategories_hierarchy", {})
            self._library_loading = False

            self._downloaded_index = _build_downloaded_index(items)
            if self._feed_items:
                self._feed_items = _mark_downloaded(self._feed_items, self._downloaded_index)
                self.feedItemsChanged.emit()

            self.libraryItemsChanged.emit()
            self.libraryTotalChanged.emit()
            self.missingModelsCountChanged.emit()
            self.subcategoriesHierarchyChanged.emit()
            self.categoriesChanged.emit()
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
            self.loadLibrary(search, category)
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

    # --- Job Status Widget Support ---

    def _job_add(self, kind: str, title: str, detail: str = "") -> int:
        """Registers a job (GUI thread). progress -1 means indeterminate."""
        self._job_seq += 1
        self._jobs.insert(0, {
            "id": self._job_seq,
            "kind": kind,
            "title": title,
            "detail": detail,
            "status": "running",
            "progress": -1.0,
            "started": time.strftime("%H:%M"),
        })
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
        from PySide6.QtCore import QThread
        if QThread.currentThread() is self.thread():
            _apply()
        else:
            self._runOnMain.emit(_apply)

    @Slot()
    def clearFinishedJobs(self):
        self._jobs = [j for j in self._jobs if j["status"] == "running"]
        self.downloadJobsChanged.emit()

    # --- Download Queue & Bulk Feeds ---

    def _refresh_queue(self):
        self._queue_items = self.queue.items()
        st = self.queue.stats()
        self._queue_stats = st
        if st["current_id"] != self._queue_progress.get("id"):
            self._queue_progress = {"id": st["current_id"], "done": 0, "total": 0}
            self.queueProgressChanged.emit()
        self.queueChanged.emit()

        busy = st["running"] or bool(st["listing"])
        done = st["finished"]
        title = f"Download queue  {done} / {st['total']}"
        if busy:
            if not self._queue_job_id or self._job_status(self._queue_job_id) != "running":
                self._queue_job_id = self._job_add("queue", title, "Starting...")
            self._job_update(
                self._queue_job_id,
                title=title,
                status="running",
                progress=(done / st["total"]) if st["total"] else -1.0,
                detail=st["listing"] or st["current_title"] or "",
            )
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

    # --- Maintenance, Storage & Cache ---

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
        chosen = QFileDialog.getExistingDirectory(None, "Choose a folder with downloaded models", str(Path.home()))
        if chosen:
            self._import_library([chosen], move)

    @Slot(bool)
    def importLibraryFiles(self, move: bool = False):
        files, _ = QFileDialog.getOpenFileNames(
            None, "Choose model archives / images", str(Path.home()),
            "Models & images (*.zip *.rar *.7z *.skp *.jpg *.jpeg *.png *.webp)",
        )
        if files:
            self._import_library(files, move)

    @Slot("QVariantList", str)
    def exportBulkZip(self, rel_folder_paths, export_type: str = "both"):
        """Exports multiple models to a single zip file."""
        paths = [str(p) for p in rel_folder_paths if p]
        if not paths:
            self.toast.emit("warning", "No models selected for export")
            return

        def _task():
            return library_manager.create_bulk_zip(paths, export_type)

        def _on_success(zip_path):
            self.toast.emit("success", f"Bulk zip created: {zip_path.name}")
            self.openFolder(str(zip_path.parent))

        def _on_error(exc):
            self.toast.emit("error", f"Bulk export failed: {exc}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    # --- Batch Re-Download Missing Models ---

    def _start_batch_download(self, scope: str, target: Any = None):
        if self._is_batch_downloading:
            self.toast.emit("warning", "A batch download is already in progress")
            return

        self._is_batch_downloading = True
        self._batch_stop_event.clear()
        self._batch_logs = []
        self._batch_progress = {
            "current": 0,
            "total": 0,
            "title": "",
            "status": "Starting batch download...",
            "percent": 0.0,
        }
        self.batchDownloadingChanged.emit()
        self.batchDownloadProgressChanged.emit()
        self.batchDownloadLogsChanged.emit()

        def _progress_cb(cur, tot, title, status, percent):
            try:
                self._batch_progress = {
                    "current": cur,
                    "total": tot,
                    "title": title,
                    "status": status,
                    "percent": percent,
                }
                self.batchDownloadProgressChanged.emit()
            except RuntimeError:
                pass

        def _log_cb(msg):
            try:
                self._batch_logs.append(msg)
                self.batchDownloadLogsChanged.emit()
                self.batchDownloadLogAdded.emit(msg)
            except RuntimeError:
                pass

        def _task():
            return self.service.batch_download_missing_models(
                scope=scope,
                target=target,
                progress_cb=_progress_cb,
                log_cb=_log_cb,
                stop_event=self._batch_stop_event,
                is_auto_retry_active=lambda: self._auto_retry_enabled,
            )

        def _on_success(res):
            self._is_batch_downloading = False
            self.batchDownloadingChanged.emit()
            succ = res.get("succeeded", 0)
            failed = res.get("failed", 0)
            total = res.get("total", 0)
            self.batchDownloadFinished.emit(succ, failed, total)

            if total == 0:
                self.toast.emit("info", "No missing models found to re-download")
            elif res.get("cancelled"):
                self.toast.emit("warning", f"Batch download stopped. {succ} downloaded, {failed} failed.")
            else:
                self.toast.emit("success", f"Batch complete: {succ} of {total} models re-downloaded successfully!")

            self.loadLibrary()
            self.refreshStatus()

        def _on_error(exc):
            self._is_batch_downloading = False
            self.batchDownloadingChanged.emit()
            self.toast.emit("error", f"Batch download failed: {exc}")
            self.loadLibrary()

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def retryMissingModel(self, folder_path: str):
        """Re-downloads missing model for a single article."""
        self._start_batch_download("article", folder_path)

    @Slot(str)
    def retryMissingModelsCategory(self, category_name: str):
        """Re-downloads all missing models in a category at once."""
        self._start_batch_download("category", category_name)

    @Slot(str, str)
    def retryMissingModelsSubcategory(self, category_name: str, subcategory_name: str):
        """Re-downloads all missing models in a subcategory at once."""
        self._start_batch_download("subcategory", {"category": category_name, "subcategory": subcategory_name})

    @Slot()
    def retryAllMissingModels(self):
        """Re-downloads all missing models in the entire library at once."""
        self._start_batch_download("all", None)

    @Slot(str, str, str, str, result="QVariant")
    def getMissingModelsForScope(
        self,
        scope: str = "all",
        category: str = "",
        subcategory: str = "",
        article_folder: str = "",
    ) -> List[Dict[str, Any]]:
        """Returns list of missing models for given scope with formatted image URLs."""
        if scope == "article":
            items = library_manager.get_missing_items("article", article_folder)
        elif scope == "category":
            items = library_manager.get_missing_items("category", category)
        elif scope == "subcategory":
            items = library_manager.get_missing_items("subcategory", (category, subcategory))
        else:
            items = library_manager.get_missing_items("all")

        formatted = []
        for it in items:
            it_copy = dict(it)
            raw_imgs = it.get("images", [])
            imgs_file_urls = []
            for rel_img in raw_imgs:
                p = (FEEDS_DIR / rel_img).resolve()
                if p.exists():
                    imgs_file_urls.append(QUrl.fromLocalFile(str(p)).toString())
            it_copy["images_full"] = imgs_file_urls
            it_copy["first_image"] = imgs_file_urls[0] if imgs_file_urls else ""
            formatted.append(it_copy)
        return formatted

    @Slot("QVariant")
    def retryMissingModelsList(self, folder_paths: Any):
        """Re-downloads a specific list of missing models by their folder paths."""
        if hasattr(folder_paths, "toVariant"):
            items = folder_paths.toVariant()
        elif isinstance(folder_paths, (list, tuple)):
            items = list(folder_paths)
        else:
            items = [folder_paths]
        clean_paths = [str(x) for x in items if x]
        self._start_batch_download("custom", clean_paths)

    @Slot()
    def cancelBatchDownload(self):
        """Signals cancellation to running batch download."""
        if self._is_batch_downloading:
            self._batch_stop_event.set()
            self.toast.emit("info", "Stopping batch download...")

    @Slot()
    def toggleAutoRetry(self):
        """Toggles the auto-retry state for batch downloading."""
        self.setAutoRetryEnabled(not self._auto_retry_enabled)

    @Slot(bool)
    def setAutoRetryEnabled(self, enabled: bool):
        """Sets the auto-retry state for batch downloading."""
        if self._auto_retry_enabled != enabled:
            self._auto_retry_enabled = enabled
            self.autoRetryEnabledChanged.emit()

    @Slot(str)
    @Slot(str, str)
    def copyToClipboard(self, text: str, message: str = ""):
        """Copies text to the system clipboard and notifies user."""
        clean_text = str(text or "").strip()
        if not clean_text:
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_text)
            if message:
                self.toast.emit("success", message)
            elif clean_text.startswith("http://") or clean_text.startswith("https://"):
                self.toast.emit("success", "Link copied to clipboard!")
            elif "\n" in clean_text or "---" in clean_text:
                self.toast.emit("success", "Logs copied to clipboard!")
            else:
                self.toast.emit("success", "Copied to clipboard!")

    # --- Clear Download List ---

    @Slot(str)
    def clearDownloadList(self, mode: str = "all"):
        """
        Clears items from the library download list.
        mode: 'all' (wipes all downloaded articles) or 'missing' (removes only incomplete articles)
        """
        self.toast.emit("info", f"Clearing download list (mode: {mode})...")

        def _task():
            return self.service.clear_library(mode=mode)

        def _on_success(count):
            self.toast.emit("success", f"Removed {count} article(s) from download list")
            self.loadLibrary()
            self.refreshStatus()

        def _on_error(exc):
            self.toast.emit("error", f"Clear download list failed: {exc}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    # --- Multi-Destination Disk Copy ---

    @Slot(str, "QVariant", "QVariant", bool)
    def startCopy(
        self,
        scope: str = "all",
        target: Any = None,
        destinations: Optional[List[str]] = None,
        include_agent: bool = True,
    ):
        """
        Copies articles by article, category, or subcategory to multiple destination disks simultaneously.
        """
        if hasattr(destinations, "toVariant"):
            destinations = destinations.toVariant()
        if hasattr(target, "toVariant"):
            target = target.toVariant()

        if self._is_copying:
            self.toast.emit("warning", "A copy operation is already in progress")
            return

        dests = destinations or settings_manager.get_copy_destinations()
        if not dests:
            self.toast.emit("warning", "Please add at least one destination disk or folder first")
            return

        self._is_copying = True
        self._copy_stop_event.clear()
        self._copy_logs = []
        self._copy_progress = {
            "current": 0,
            "total": 0,
            "title": "",
            "currentDest": "",
            "percent": 0.0,
            "bytesText": "0 B",
        }
        self.isCopyingChanged.emit()
        self.copyProgressChanged.emit()
        self.copyLogsChanged.emit()

        def _progress_cb(cur, tot, title, dest_name, percent, bytes_text):
            self._copy_progress = {
                "current": cur,
                "total": tot,
                "title": title,
                "currentDest": dest_name,
                "percent": percent,
                "bytesText": bytes_text,
            }
            self.copyProgressChanged.emit()

        def _log_cb(msg):
            self._copy_logs.append(msg)
            self.copyLogsChanged.emit()
            self.copyLogAdded.emit(msg)

        def _task():
            return self.service.copy_articles(
                scope=scope,
                target=target,
                destinations=dests,
                include_client_agent=include_agent,
                progress_cb=_progress_cb,
                log_cb=_log_cb,
                stop_event=self._copy_stop_event,
            )

        def _on_success(res):
            self._is_copying = False
            self.isCopyingChanged.emit()
            if res.get("success"):
                copied = res.get("copied_articles", 0)
                tot_dests = res.get("destinations_count", len(dests))
                bytes_txt = res.get("total_bytes_text", "")
                agent_copied = res.get("client_agent_copied", 0)

                msg = f"Copied {copied} articles ({bytes_txt}) to {tot_dests} destination disk(s)!"
                if agent_copied > 0:
                    msg += " Client agent included."

                self.toast.emit("success", msg)
                self.copyFinished.emit(True, msg)
            else:
                err = res.get("error", "Copy failed")
                self.toast.emit("error", err)
                self.copyFinished.emit(False, err)

        def _on_error(exc):
            self._is_copying = False
            self.isCopyingChanged.emit()
            err_msg = str(exc)
            self.toast.emit("error", f"Copy error: {err_msg}")
            self.copyFinished.emit(False, err_msg)

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot()
    def cancelCopy(self):
        """Signals cancellation to running copy operation."""
        if self._is_copying:
            self._copy_stop_event.set()
            self.toast.emit("info", "Cancelling copy operation...")

    # Loft Design API Slots
    @Slot(str, str, str)
    def setApiConfig(self, url: str, username: str, password: str):
        """Saves Loft Design API URL and credentials."""
        settings_manager.set_api_url(url)
        settings_manager.set_api_username(username)
        settings_manager.set_api_password(password)
        self.apiUrlChanged.emit()
        self.apiUsernameChanged.emit()
        self.apiPasswordChanged.emit()
        self.toast.emit("success", "Loft Design API credentials saved")

    @Slot(str, str)
    def setApiCredentials(self, username: str, password: str):
        """Saves Loft Design API credentials using static API URL."""
        settings_manager.set_api_username(username)
        settings_manager.set_api_password(password)
        self.apiUsernameChanged.emit()
        self.apiPasswordChanged.emit()
        self.toast.emit("success", "Loft Design API credentials saved")

    @Slot(str, str)
    def testApiCredentials(self, username: str, password: str):
        """Tests Loft Design API connectivity using provided credentials with static URL."""
        self.testApiConnectionWithCredentials(
            settings_manager.DEFAULT_API_URL,
            username,
            password,
        )

    @Slot(result="QVariant")
    def getApiConfig(self) -> Dict[str, str]:
        """Returns current Loft Design API configuration."""
        return settings_manager.get_api_config()

    @Slot(str, str, str)
    def testApiConnectionWithCredentials(self, url: str, username: str, password: str):
        """Tests Loft Design API connectivity using provided credentials in background."""
        def _task():
            return self.service.test_api_connection(
                api_url=url,
                username=username,
                password=password,
            )

        def _on_success(res):
            success, message = res
            self.apiConnectionTested.emit(success, message)
            if success:
                self.toast.emit("success", f"API Connected: {message}")
            else:
                self.toast.emit("error", f"Connection Failed: {message}")

        def _on_error(exc):
            msg = str(exc)
            self.apiConnectionTested.emit(False, msg)
            self.toast.emit("error", f"Connection Test Error: {msg}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot()
    def testApiConnection(self):
        """Tests connection with currently stored API credentials."""
        self.testApiConnectionWithCredentials(
            settings_manager.get_api_url(),
            settings_manager.get_api_username(),
            settings_manager.get_api_password(),
        )

    # Article Upload Slots
    def _start_upload(self, scope: str, target: Any = None):
        """Internal helper to launch background article upload."""
        if self._is_uploading:
            self.toast.emit("warning", "An upload is already in progress")
            return

        api_url = settings_manager.get_api_url()
        username = settings_manager.get_api_username()
        password = settings_manager.get_api_password()

        if not username or not password:
            self.toast.emit("error", "API credentials missing. Please configure username & password in Settings.")
            self.uploadFinished.emit(0, 0, 0)
            return

        self._is_uploading = True
        self._upload_stop_event.clear()
        self._upload_logs = []
        self._upload_progress = {
            "current": 0,
            "total": 0,
            "title": "",
            "status": "Starting upload...",
            "percent": 0.0,
        }
        self.isUploadingChanged.emit()
        self.uploadProgressChanged.emit()
        self.uploadLogsChanged.emit()

        def _progress_cb(cur, tot, title, status, percent):
            try:
                self._upload_progress = {
                    "current": cur,
                    "total": tot,
                    "title": title,
                    "status": status,
                    "percent": percent,
                }
                self.uploadProgressChanged.emit()
            except RuntimeError:
                pass

        def _log_cb(msg):
            try:
                self._upload_logs.append(msg)
                self.uploadLogsChanged.emit()
                self.uploadLogAdded.emit(msg)
            except RuntimeError:
                pass

        def _task():
            return self.service.upload_articles(
                scope=scope,
                target=target,
                api_url=api_url,
                username=username,
                password=password,
                progress_cb=_progress_cb,
                log_cb=_log_cb,
                stop_event=self._upload_stop_event,
            )

        def _on_success(res):
            self._is_uploading = False
            self.isUploadingChanged.emit()
            succ = res.get("succeeded", 0)
            failed = res.get("failed", 0)
            total = res.get("total", 0)
            self.uploadFinished.emit(succ, failed, total)

            if total == 0:
                self.toast.emit("info", "No articles found to upload")
            elif res.get("cancelled"):
                self.toast.emit("warning", f"Upload stopped. {succ} uploaded, {failed} failed.")
            else:
                self.toast.emit("success", f"Upload complete: {succ} of {total} articles uploaded successfully!")

        def _on_error(exc):
            self._is_uploading = False
            self.isUploadingChanged.emit()
            self.uploadFinished.emit(0, 0, 0)
            self.toast.emit("error", f"Upload failed: {exc}")

        self.thread_pool.start(Worker(_task, on_success=_on_success, on_error=_on_error))

    @Slot(str)
    def uploadArticle(self, folder_path: str):
        """Uploads a single article to Loft Design API."""
        self._start_upload("article", folder_path)

    @Slot(str)
    def uploadCategory(self, category_name: str):
        """Uploads all articles in a category to Loft Design API."""
        self._start_upload("category", category_name)

    @Slot(str, str)
    def uploadSubcategory(self, category_name: str, subcategory_name: str):
        """Uploads all articles in a subcategory to Loft Design API."""
        self._start_upload("subcategory", {"category": category_name, "subcategory": subcategory_name})

    @Slot()
    def uploadAllArticles(self):
        """Uploads all articles in the library to Loft Design API."""
        self._start_upload("all", None)

    @Slot("QVariant")
    def uploadArticlesList(self, folder_paths: Any):
        """Uploads a specific list of articles by their folder paths."""
        if hasattr(folder_paths, "toVariant"):
            items = folder_paths.toVariant()
        elif isinstance(folder_paths, (list, tuple)):
            items = list(folder_paths)
        else:
            items = [folder_paths]
        clean_paths = [str(x) for x in items if x]
        self._start_upload("custom", clean_paths)

    @Slot(str, str, str, str, result="QVariant")
    def getUploadArticlesForScope(
        self,
        scope: str = "all",
        category: str = "",
        subcategory: str = "",
        article_folder: str = "",
    ) -> List[Dict[str, Any]]:
        """Returns list of articles matching scope formatted for upload selection preview."""
        if scope == "article":
            items = library_manager.get_articles_by_scope("article", article_folder)
        elif scope == "category":
            items = library_manager.get_articles_by_scope("category", category)
        elif scope == "subcategory":
            items = library_manager.get_articles_by_scope("subcategory", (category, subcategory))
        else:
            items = library_manager.get_articles_by_scope("all")

        formatted = []
        for it in items:
            it_copy = dict(it)
            raw_imgs = it.get("images", [])
            imgs_file_urls = []
            for rel_img in raw_imgs:
                p = (FEEDS_DIR / rel_img).resolve()
                if p.exists():
                    imgs_file_urls.append(QUrl.fromLocalFile(str(p)).toString())
            it_copy["images_full"] = imgs_file_urls
            it_copy["first_image"] = imgs_file_urls[0] if imgs_file_urls else ""
            formatted.append(it_copy)
        return formatted

    @Slot()
    def cancelUpload(self):
        """Signals cancellation to running upload."""
        if self._is_uploading:
            self._upload_stop_event.set()
            self.toast.emit("info", "Stopping upload...")

    @Slot()
    def clearUploadLogs(self):
        """Clears upload log history."""
        self._upload_logs = []
        self.uploadLogsChanged.emit()

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
        self.openFolder(folder_path)

    @Slot(str)
    def openWeb(self, url: str):
        """Opens URL in external default browser."""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(str)
    def openExternalUrl(self, url: str):
        self.openWeb(url)
