"""
Multi-Destination Disk Copy Manager for CGTips 3D Desktop.
Copies articles by Article, Category, or Subcategory to multiple destination disks simultaneously.
Automatically includes configured Client Agent executable.
"""

import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import FEEDS_DIR
from .library import library_manager, format_bytes
from .settings_manager import settings_manager

logger = logging.getLogger("copy_manager")


def _copy_stream_to_destinations(
    src_file: Path,
    dst_files: List[Path],
    stop_event: Optional[threading.Event] = None,
    chunk_size: int = 1024 * 1024,  # 1 MB chunk
) -> int:
    """Streams data from src_file to multiple destination files simultaneously in one read pass."""
    total_bytes = 0
    file_handles = []

    try:
        with open(src_file, "rb") as sf:
            for df in dst_files:
                df.parent.mkdir(parents=True, exist_ok=True)
                file_handles.append(open(df, "wb"))

            while True:
                if stop_event and stop_event.is_set():
                    break
                chunk = sf.read(chunk_size)
                if not chunk:
                    break
                for fh in file_handles:
                    fh.write(chunk)
                total_bytes += len(chunk)
    finally:
        for fh in file_handles:
            try:
                fh.flush()
                fh.close()
            except Exception:
                pass

    # Preserve file modification timestamps
    try:
        stat = src_file.stat()
        for df in dst_files:
            if df.exists():
                os.utime(df, (stat.st_atime, stat.st_mtime))
    except Exception:
        pass

    return total_bytes


class CopyManager:
    def __init__(self):
        self._lock = threading.Lock()

    def copy_articles(
        self,
        scope: str = "all",
        target: Any = None,
        destinations: Optional[List[str]] = None,
        include_client_agent: bool = True,
        client_agent_path: Optional[str] = None,
        progress_cb: Optional[Callable[[int, int, str, str, float, str], None]] = None,
        log_cb: Optional[Callable[[str], None]] = None,
        stop_event: Optional[threading.Event] = None,
        library_mgr: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Copies articles to multiple destination disks/folders simultaneously.
        scope: "article" | "subcategory" | "category" | "all"
        target:
          - for "article": folder_path
          - for "subcategory": {"category": ..., "subcategory": ...}
          - for "category": category_name
        destinations: list of destination disk/folder paths
        include_client_agent: if True, auto-copies the client agent exe to each destination root
        progress_cb: fn(current_item_idx, total_items, item_title, dest_name, percent, bytes_text)
        log_cb: fn(message)
        """
        def _log(msg: str):
            if log_cb:
                log_cb(msg)
            logger.info(msg)

        lib = library_mgr or library_manager
        base_feeds = lib.base_dir.resolve()

        # 1. Resolve and validate destination directories
        raw_dests = destinations or settings_manager.get_copy_destinations()
        valid_dests: List[Path] = []
        for d in raw_dests:
            dp = Path(str(d).strip()).resolve()
            try:
                dp.mkdir(parents=True, exist_ok=True)
                # Test writability
                test_file = dp / ".cgtips_write_test"
                test_file.write_text("ok")
                test_file.unlink()
                valid_dests.append(dp)
            except Exception as e:
                _log(f"⚠️ Destination unavailable or not writable: {dp} ({e})")

        if not valid_dests:
            _log("❌ No valid destination disks/folders selected or writable.")
            return {
                "success": False,
                "error": "No valid destination disks or folders selected.",
                "total_articles": 0,
                "copied_articles": 0,
                "destinations": 0,
            }

        _log(f"Targeting {len(valid_dests)} destination disk(s):")
        for vd in valid_dests:
            _log(f"  • {vd}")

        # 2. Gather articles by scope
        articles = lib.get_articles_by_scope(scope=scope, target=target)
        total_articles = len(articles)

        if total_articles == 0:
            _log(f"No articles found matching scope '{scope}'")
            return {
                "success": True,
                "total_articles": 0,
                "copied_articles": 0,
                "destinations": len(valid_dests),
                "cancelled": False,
            }

        _log(f"Found {total_articles} article(s) to copy.")

        # 3. Handle Client Agent Executable Auto-Copy
        agent_path_str = client_agent_path or settings_manager.get_client_agent_path()
        agent_copied_count = 0
        if include_client_agent and agent_path_str:
            agent_file = Path(agent_path_str).resolve()
            if agent_file.exists() and agent_file.is_file():
                _log(f"Client Agent identified: {agent_file.name}")
                for dest in valid_dests:
                    try:
                        dest_agent = dest / agent_file.name
                        shutil.copy2(agent_file, dest_agent)
                        agent_copied_count += 1
                        _log(f"✓ Copied client agent to {dest_agent}")
                    except Exception as ce:
                        _log(f"⚠️ Failed copying client agent to {dest}: {ce}")
            else:
                _log(f"⚠️ Client agent path specified but not found on disk: {agent_file}")
        elif include_client_agent:
            _log("ℹ️ No client agent executable configured in Settings (skipping agent copy).")

        # 4. Copy each article to all destinations simultaneously
        copied_articles = 0
        total_bytes_copied = 0
        cancelled = False

        for idx, art in enumerate(articles):
            if stop_event and stop_event.is_set():
                _log("Copy operation cancelled by user.")
                cancelled = True
                break

            title = art.get("title", "Article")
            rel_folder = art.get("folder_path", "")
            src_folder = (base_feeds / rel_folder).resolve()

            percent = (idx / total_articles) * 100.0
            bytes_str = format_bytes(total_bytes_copied)

            if progress_cb:
                progress_cb(
                    idx + 1,
                    total_articles,
                    title,
                    f"Copying to {len(valid_dests)} destinations",
                    percent,
                    bytes_str,
                )

            _log(f"\n[{idx + 1}/{total_articles}] Copying article: {title}")

            if not src_folder.exists():
                _log(f"⚠️ Source folder not found: {src_folder}")
                continue

            # Gather all files in this article directory
            all_files = [f for f in src_folder.rglob("*") if f.is_file() and not f.name.startswith(".")]

            for src_file in all_files:
                if stop_event and stop_event.is_set():
                    cancelled = True
                    break

                rel_file = src_file.resolve().relative_to(base_feeds)
                target_dest_files = [dest / rel_file for dest in valid_dests]

                try:
                    bytes_written = _copy_stream_to_destinations(
                        src_file, target_dest_files, stop_event=stop_event
                    )
                    total_bytes_copied += bytes_written
                except Exception as fe:
                    _log(f"⚠️ Error copying file {src_file.name}: {fe}")

            copied_articles += 1

        final_percent = 100.0 if not cancelled else ((copied_articles) / max(total_articles, 1)) * 100.0
        final_bytes_str = format_bytes(total_bytes_copied)

        if progress_cb:
            progress_cb(
                copied_articles,
                total_articles,
                "Finished",
                f"Copied {copied_articles} articles to {len(valid_dests)} disks",
                final_percent,
                final_bytes_str,
            )

        _log(f"\n=== Copy Complete: {copied_articles}/{total_articles} articles copied ({final_bytes_str}) ===")

        return {
            "success": True,
            "total_articles": total_articles,
            "copied_articles": copied_articles,
            "destinations_count": len(valid_dests),
            "client_agent_copied": agent_copied_count,
            "total_bytes_copied": total_bytes_copied,
            "total_bytes_text": final_bytes_str,
            "cancelled": cancelled,
        }


# Singleton copy manager instance
copy_manager = CopyManager()
