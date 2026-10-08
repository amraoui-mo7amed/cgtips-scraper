"""
Download queue: articles waiting to be downloaded, processed one at a time with a
single shared browser. It can be paused and resumed (a model download in progress
keeps its partial file and continues from there), failed items can be retried, and
the queue is saved to data/download_queue.json so it survives a restart.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import config
import history
from browser_manager import BrowserManager
from config import HEADLESS
from engine import (
    _article_complete,
    article_folder_for,
    download_model_only,
    resolve_and_download_single_article,
    sanitize,
    write_meta,
)
from utils import DownloadPaused, get_feed

logger = logging.getLogger("queue")

ACTIVE = ("pending", "paused", "downloading")


class DownloadQueue:
    def __init__(
        self,
        on_change: Optional[Callable[[], None]] = None,
        on_progress: Optional[Callable[[int, int, int], None]] = None,
        on_item_done: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self._on_change = on_change or (lambda: None)
        self._on_progress = on_progress or (lambda *_: None)
        self._on_item_done = on_item_done or (lambda _item: None)
        self._lock = threading.RLock()
        self._items: List[Dict[str, Any]] = []
        self._next_id = 1
        self._cancel = threading.Event()   # set = pause the item being downloaded
        self._worker: Optional[threading.Thread] = None
        self.paused = False
        self.listing = ""                  # "Listing Furniture › Sofa" while feeds are read
        self._load()

    # --- persistence -------------------------------------------------------

    @staticmethod
    def _file() -> Path:
        return Path(config.DATA_DIR) / "download_queue.json"

    def _load(self):
        try:
            data = json.loads(self._file().read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except Exception as e:
            logger.warning("Could not read the download queue: %s", e)
            return
        self._items = [i for i in data.get("items", []) if isinstance(i, dict) and i.get("link")]
        for it in self._items:
            if it.get("status") == "downloading":
                it["status"] = "paused"  # the app closed mid-download; its partial file is kept
        self._next_id = max([i.get("id", 0) for i in self._items] + [0]) + 1
        # Leftover work waits for the user (or the next "add") instead of starting on its own.
        self.paused = any(i["status"] in ACTIVE for i in self._items)

    def _save(self):
        f = self._file()
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"version": 1, "items": self._items}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(f)

    def _changed(self):
        with self._lock:
            self._save()
        self._on_change()

    # --- reading -----------------------------------------------------------

    def items(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(i) for i in self._items]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            counts = {k: 0 for k in ("pending", "paused", "downloading", "done", "skipped", "failed")}
            for i in self._items:
                counts[i["status"]] = counts.get(i["status"], 0) + 1
            current = next((i for i in self._items if i["status"] == "downloading"), None)
            return dict(
                counts,
                total=len(self._items),
                active=counts["pending"] + counts["paused"] + counts["downloading"],
                finished=counts["done"] + counts["skipped"] + counts["failed"],
                running=self.is_running(),
                is_paused=self.paused,
                listing=self.listing,
                current_id=current["id"] if current else 0,
                current_title=current["title"] if current else "",
            )

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    # --- adding ------------------------------------------------------------

    def add_articles(self, articles: List[Dict[str, Any]], category: str, subcategory: str,
                     models: bool = True, images: bool = True, start: bool = True) -> int:
        added = 0
        with self._lock:
            by_link = {i["link"]: i for i in self._items}
            for a in articles:
                link = (a.get("link") or "").strip()
                if not link:
                    continue
                old = by_link.get(link)
                if old is not None and old["status"] in ACTIVE:
                    continue  # already waiting
                if old is not None:
                    self._items.remove(old)  # finished or failed before: queue it again
                item = {
                    "id": self._next_id, "title": a.get("title") or link, "link": link,
                    "category": category, "subcategory": subcategory,
                    "models": bool(models), "images": bool(images),
                    "status": "pending", "error": "", "attempts": 0,
                    "gdrive_url": "", "folder": "", "bytes_done": 0, "bytes_total": 0,
                    "added": time.strftime("%Y-%m-%d %H:%M"), "finished": "",
                }
                self._next_id += 1
                self._items.append(item)
                by_link[link] = item
                added += 1
        self._changed()
        if start and added:
            self.resume()
        return added

    def add_feeds(self, groups: List[Dict[str, Any]], max_items: int = 0, models: bool = True,
                  images: bool = True, start: bool = True, done_cb: Optional[Callable[[int], None]] = None):
        """Reads each sub-category feed (in the background) and queues its articles."""
        def _list():
            total = 0
            try:
                for g in groups:
                    self.listing = f"Listing {g.get('category', '')} › {g.get('subcategory', '')}"
                    self._on_change()
                    try:
                        arts = get_feed(feed_url=g["feed_url"], max_items=max_items) if g.get("feed_url") else []
                    except Exception as e:
                        logger.warning("Could not read feed for %s: %s", g.get("subcategory"), e)
                        arts = []
                    total += self.add_articles(arts, g.get("category", ""), g.get("subcategory", ""),
                                               models, images, start=start)
            finally:
                self.listing = ""
                self._on_change()
                if done_cb:
                    done_cb(total)

        threading.Thread(target=_list, name="queue-listing", daemon=True).start()

    # --- controls ----------------------------------------------------------

    def pause(self):
        self.paused = True
        self._cancel.set()
        self._on_change()

    def resume(self):
        with self._lock:
            self.paused = False
            self._cancel.clear()
            if not self.is_running() and any(i["status"] in ("pending", "paused") for i in self._items):
                self._worker = threading.Thread(target=self._run, name="download-queue", daemon=True)
                self._worker.start()
        self._on_change()

    def retry(self, item_id: int):
        with self._lock:
            for i in self._items:
                if i["id"] == item_id and i["status"] in ("failed", "skipped", "done"):
                    i.update(status="pending", error="")
        self._changed()
        self.resume()

    def retry_failed(self) -> int:
        with self._lock:
            failed = [i for i in self._items if i["status"] == "failed"]
            for i in failed:
                i.update(status="pending", error="")
        self._changed()
        if failed:
            self.resume()
        return len(failed)

    def remove(self, item_id: int):
        with self._lock:
            self._items = [i for i in self._items if not (i["id"] == item_id and i["status"] != "downloading")]
        self._changed()

    def move_to_top(self, item_id: int):
        with self._lock:
            it = next((i for i in self._items if i["id"] == item_id), None)
            if it is not None and it["status"] in ("pending", "paused"):
                self._items.remove(it)
                first = next((n for n, i in enumerate(self._items) if i["status"] in ACTIVE), len(self._items))
                self._items.insert(first, it)
        self._changed()

    def clear_finished(self) -> int:
        with self._lock:
            before = len(self._items)
            self._items = [i for i in self._items if i["status"] in ACTIVE or i["status"] == "failed"]
            removed = before - len(self._items)
        self._changed()
        return removed

    # --- worker ------------------------------------------------------------

    def _next(self) -> Optional[Dict[str, Any]]:
        # An item interrupted by a pause continues before new ones start.
        for status in ("paused", "pending"):
            for i in self._items:
                if i["status"] == status:
                    return i
        return None

    def _run(self):
        browser = {"bm": None, "p_ctx": None, "context": None, "page": None}

        def _page():
            if browser["page"] is None:
                browser["bm"] = BrowserManager(headless=HEADLESS)
                browser["p_ctx"], browser["context"] = browser["bm"].get_context()
                browser["page"] = browser["context"].new_page()
            return browser["page"]

        def _close():
            try:
                if browser["context"]:
                    browser["context"].close()
                if browser["p_ctx"]:
                    browser["p_ctx"].stop()
            except Exception:
                pass
            browser.update(bm=None, p_ctx=None, context=None, page=None)

        try:
            while True:
                with self._lock:
                    if self.paused:
                        break
                    item = self._next()
                    if item is None:
                        break
                    item.update(status="downloading", error="")
                self._changed()
                ok_browser = self._process(item, _page)
                if not ok_browser:
                    _close()  # next article starts from a fresh browser
                self._changed()
        except Exception:
            logger.exception("Download queue stopped unexpectedly")
        finally:
            _close()
            with self._lock:
                self._worker = None
            self._on_change()

    def _process(self, item: Dict[str, Any], get_page) -> bool:
        """Downloads one item and sets its final status. Returns False if the browser should be reset."""
        label = item["title"][:70]
        folder = article_folder_for(item["category"], item["subcategory"], item["title"])
        resume_model = bool(item.get("gdrive_url") and item.get("folder") and item["models"])

        if not resume_model:
            if item["models"] and history.has(item["link"], item["title"]):
                self._finish(item, "skipped", "Already downloaded (download history)")
                return True
            if _article_complete(folder, item["models"], item["images"]):
                item["folder"] = str(folder)
                self._finish(item, "skipped", "Already in the library")
                return True

        last = [0.0]

        def _bytes(done: int, total: int, _name: str = ""):
            item.update(bytes_done=done, bytes_total=total)
            if time.monotonic() - last[0] > 0.4 or (total and done >= total):
                last[0] = time.monotonic()
                self._on_progress(item["id"], done, total)

        try:
            page = get_page()
            if resume_model:
                logger.info("Queue: continuing model of %s", label)
                model_file = download_model_only(item["gdrive_url"], Path(item["folder"]), page=page,
                                                 progress_cb=_bytes, cancel_event=self._cancel)
                if model_file:
                    history.add(item["link"], item["title"], item["category"], item["subcategory"])
                    self._finish(item, "done")
                else:
                    self._finish(item, "failed", "Model download failed (Drive quota or file unreachable)")
                return True

            dest = config.FEEDS_DIR / (sanitize(item["category"]) or "Imported") / (sanitize(item["subcategory"]) or "Imported")
            res = resolve_and_download_single_article(
                item["link"], download_model=item["models"], download_imgs=item["images"], dest_dir=dest,
                progress_cb=_bytes, page=page, title_hint=item["title"], cancel_event=self._cancel,
            )
            if res.get("folder"):
                item["folder"] = res["folder"]
                write_meta(Path(res["folder"]), article_url=item["link"],
                           category=item["category"], subcategory=item["subcategory"])
            if res.get("gdrive_url"):
                item["gdrive_url"] = res["gdrive_url"]  # a retry can go straight to the model
            ok = bool(res.get("success")) or (not item["models"] and bool(res.get("images")))
            if ok:
                self._finish(item, "done")
                return True
            self._finish(item, "failed", res.get("error") or (
                "Model download failed (Drive quota or file unreachable)" if item.get("gdrive_url")
                else "No download link found"))
            return False
        except DownloadPaused as p:
            with self._lock:
                item.update(status="paused", gdrive_url=p.gdrive_url or item.get("gdrive_url", ""),
                            folder=p.folder or item.get("folder", ""))
            logger.info("Queue: paused %s at %d bytes", label, item.get("bytes_done", 0))
            return True
        except Exception as e:
            logger.warning("Queue: %s failed: %s", label, e)
            self._finish(item, "failed", str(e)[:300])
            return False

    def _finish(self, item: Dict[str, Any], status: str, error: str = ""):
        with self._lock:
            item.update(status=status, error=error, finished=time.strftime("%Y-%m-%d %H:%M"))
            if status in ("done", "failed"):
                item["attempts"] = item.get("attempts", 0) + 1
            if status == "done":
                item["gdrive_url"] = ""
        if status == "done" and item.get("folder"):
            self._on_item_done(dict(item))
