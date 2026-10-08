"""
Batch Downloader for Re-Downloading Missing 3D Models.
Supports scoping by Article, Subcategory, Category, or Entire Library.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import FEEDS_DIR
from engine import resolve_and_download_single_article
from .library import library_manager

logger = logging.getLogger("batch_downloader")


def batch_download_missing(
    scope: str = "all",
    target: Any = None,
    progress_cb: Optional[Callable[[int, int, str, str, float], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None,
    library_mgr: Optional[Any] = None,
    download_fn: Optional[Callable] = None,
    is_auto_retry_active: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Finds missing 3D models matching the scope and re-downloads them.
    scope: "article" | "subcategory" | "category" | "all" | "custom"
    target:
      - for "article": folder_path
      - for "subcategory": {"category": ..., "subcategory": ...}
      - for "category": category_name
      - for "custom": list of folder_paths
    progress_cb: fn(current_index, total_count, item_title, status_text, percent)
    log_cb: fn(message)
    stop_event: threading.Event to signal cancellation
    is_auto_retry_active: fn() -> bool returning whether continuous retry is enabled
    """
    import time

    def _log(msg: str):
        if log_cb:
            try:
                log_cb(msg)
            except RuntimeError:
                pass
        logger.info(msg)

    lib = library_mgr or library_manager
    base_feeds = lib.base_dir.resolve()

    if scope == "custom" and isinstance(target, (list, tuple)):
        all_articles = lib.scan_library().get("items", [])
        folder_set = set(t.get("folder_path", t) if isinstance(t, dict) else str(t) for t in target)
        articles = [it for it in all_articles if (it["folder_path"] in folder_set or it["id"] in folder_set)]
    elif scope == "article":
        articles = lib.get_articles_by_scope(scope="article", target=target)
    else:
        articles = lib.get_missing_items(scope=scope, target=target)

    total_targeted = len(articles)
    if total_targeted == 0:
        _log(f"No missing models found for scope '{scope}'")
        return {"total": 0, "succeeded": 0, "failed": 0, "cancelled": False}

    _log(f"Found {total_targeted} model(s) to download for scope '{scope}'")

    succeeded_folders = set()
    cancelled = False
    retry_round = 1
    articles_to_process = list(articles)

    while articles_to_process and not cancelled:
        if retry_round > 1:
            _log(f"\n==========================================")
            _log(f"🔁 Auto-Retry Round {retry_round}: Retrying {len(articles_to_process)} model(s)")
            _log(f"==========================================")

        current_batch = list(articles_to_process)
        for idx, item in enumerate(current_batch):
            if stop_event and stop_event.is_set():
                _log("Batch download stopped by user.")
                cancelled = True
                break

            title = item.get("title", "3D Model")
            folder_rel = item.get("folder_path", "")
            article_dir = (base_feeds / folder_rel).resolve()

            done_count = len(succeeded_folders) + idx
            percent = (done_count / max(total_targeted, 1)) * 100.0

            status_str = f"Processing {done_count + 1}/{total_targeted}: {title}"
            if retry_round > 1:
                status_str += f" (Round {retry_round})"

            if progress_cb:
                progress_cb(min(done_count + 1, total_targeted), total_targeted, title, status_str, percent)

            _log(f"\n--- [{done_count + 1}/{total_targeted}] Processing: {title} ---")

            # 1. Check / Resolve Article URL
            article_url = item.get("article_url")
            if not article_url:
                _log(f"Resolving article URL for '{title}'...")
                article_url = lib.find_article_url(title, article_dir)

            if not article_url:
                _log(f"Could not resolve article URL for: {title}")
                continue

            _log(f"Article URL: {article_url}")

            # 2. Download model into existing article folder
            try:
                fn = download_fn or resolve_and_download_single_article
                res = fn(
                    article_url=article_url,
                    download_model=True,
                    download_imgs=False,
                    target_article_dir=article_dir,
                    log_cb=_log,
                )

                # Check if model file was obtained
                model_folder = article_dir / "model"
                has_file = False
                if model_folder.exists():
                    has_file = any(f.is_file() and not f.name.startswith(".") for f in model_folder.iterdir())

                if res.get("success") or has_file:
                    succeeded_folders.add(folder_rel)
                    _log(f"✓ Successfully downloaded model for '{title}'")
                else:
                    _log(f"✗ Model download failed for '{title}'")
            except Exception as exc:
                _log(f"✗ Exception during model download for '{title}': {exc}")

        if cancelled or (stop_event and stop_event.is_set()):
            cancelled = True
            break

        # Check remaining missing models on disk
        remaining_missing = []
        for it in articles:
            f_rel = it.get("folder_path", "")
            if f_rel in succeeded_folders:
                continue
            art_p = (base_feeds / f_rel).resolve()
            m_p = art_p / "model"
            if m_p.exists() and any(f.is_file() and not f.name.startswith(".") for f in m_p.iterdir()):
                succeeded_folders.add(f_rel)
            else:
                remaining_missing.append(it)

        if not remaining_missing:
            _log(f"\n🎉 All {len(succeeded_folders)} model(s) downloaded successfully!")
            break

        # Check if auto-retry is active
        should_retry = bool(is_auto_retry_active and is_auto_retry_active())
        if not should_retry:
            _log(f"\n=== Batch Download Finished: {len(succeeded_folders)}/{total_targeted} succeeded, {len(remaining_missing)} failed ===")
            break

        retry_round += 1
        _log(f"\n🔁 Auto-Retry is active: {len(remaining_missing)} model(s) remaining. Waiting 4 seconds before next attempt... (Round {retry_round})")

        # Wait 4 seconds, checking stop_event / is_auto_retry_active every 200ms
        for _ in range(20):
            if stop_event and stop_event.is_set():
                cancelled = True
                break
            if is_auto_retry_active and not is_auto_retry_active():
                _log("Auto-retry disabled by user. Stopping retry loop.")
                should_retry = False
                break
            time.sleep(0.2)

        if cancelled or not should_retry:
            break

        articles_to_process = remaining_missing

    final_succ = len(succeeded_folders)
    final_failed = total_targeted - final_succ
    final_percent = 100.0 if not cancelled and final_failed == 0 else (final_succ / max(total_targeted, 1)) * 100.0

    if progress_cb:
        progress_cb(
            final_succ,
            total_targeted,
            "Finished",
            f"Completed: {final_succ} succeeded, {final_failed} failed",
            final_percent,
        )

    return {
        "total": total_targeted,
        "succeeded": final_succ,
        "failed": final_failed,
        "cancelled": cancelled,
    }
