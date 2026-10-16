"""
Multi-Destination Disk Copy Manager for CGTips 3D Desktop.
Copies articles by Article, Category, or Subcategory to multiple destination disks simultaneously.
Automatically includes configured Client Agent executable.
"""

import logging
import os
import shutil
import sys
import threading
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import FEEDS_DIR
from .library import library_manager, format_bytes
from .settings_manager import settings_manager

logger = logging.getLogger("copy_manager")


def get_connected_flash_drives() -> List[Dict[str, Any]]:
    """
    Detects external/removable flash drives, USB sticks, and external disks.
    Works across macOS, Windows, and Linux.
    """
    drives = []

    if sys.platform == "darwin":
        volumes_dir = Path("/Volumes")
        if volumes_dir.exists():
            for p in sorted(volumes_dir.iterdir()):
                if not p.is_dir() or p.name.startswith("."):
                    continue
                try:
                    rp = os.path.realpath(p)
                    if rp == "/" or rp.startswith("/System") or rp == os.path.realpath(Path.home()):
                        continue
                    usage = shutil.disk_usage(p)
                    total_str = format_bytes(usage.total)
                    free_str = format_bytes(usage.free)
                    drives.append({
                        "path": str(p),
                        "name": p.name,
                        "label": f"{p.name} ({free_str} free of {total_str})",
                        "free_bytes": usage.free,
                        "total_bytes": usage.total,
                        "free_text": free_str,
                        "total_text": total_str,
                    })
                except Exception:
                    pass
    elif sys.platform == "win32":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    # 2 = DRIVE_REMOVABLE (Flash drives, USB sticks)
                    # 3 = DRIVE_FIXED (External USB HDDs / SSDs or secondary drives, skip C:)
                    if drive_type in (2, 3) and letter != "C":
                        try:
                            vol_name_buf = ctypes.create_unicode_buffer(1024)
                            ctypes.windll.kernel32.GetVolumeInformationW(
                                drive_path, vol_name_buf, 1024, None, None, None, None, 0
                            )
                            vol_name = vol_name_buf.value or f"Drive ({letter}:)"
                            usage = shutil.disk_usage(drive_path)
                            total_str = format_bytes(usage.total)
                            free_str = format_bytes(usage.free)
                            drives.append({
                                "path": drive_path,
                                "name": vol_name,
                                "label": f"{vol_name} [{letter}:] ({free_str} free of {total_str})",
                                "free_bytes": usage.free,
                                "total_bytes": usage.total,
                                "free_text": free_str,
                                "total_text": total_str,
                            })
                        except Exception:
                            pass
                bitmask >>= 1
        except Exception:
            pass
    else:
        # Linux
        candidates = [
            Path(f"/media/{os.environ.get('USER', '')}"),
            Path(f"/run/media/{os.environ.get('USER', '')}"),
            Path("/mnt"),
        ]
        for base in candidates:
            if base.exists():
                for p in sorted(base.iterdir()):
                    if p.is_dir() and not p.name.startswith("."):
                        try:
                            usage = shutil.disk_usage(p)
                            total_str = format_bytes(usage.total)
                            free_str = format_bytes(usage.free)
                            drives.append({
                                "path": str(p),
                                "name": p.name,
                                "label": f"{p.name} ({free_str} free of {total_str})",
                                "free_bytes": usage.free,
                                "total_bytes": usage.total,
                                "free_text": free_str,
                                "total_text": total_str,
                            })
                        except Exception:
                            pass

    return drives


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

        _log(f"Targeting {len(valid_dests)} destination disk(s) (copying to 'storage' folder):")
        for vd in valid_dests:
            storage_path = vd if vd.name.lower() == "storage" else vd / "storage"
            _log(f"  • {vd} -> {storage_path}")

        # 2. Gather articles by scope and FILTER ONLY FINISHED MODELS
        raw_articles = lib.get_articles_by_scope(scope=scope, target=target)
        articles = [a for a in raw_articles if a.get("has_model")]
        total_articles = len(articles)

        if total_articles == 0:
            skipped_incomplete = len(raw_articles)
            msg = f"No finished 3D models found matching scope '{scope}'"
            if skipped_incomplete > 0:
                msg += f" ({skipped_incomplete} incomplete articles with only images were skipped)"
            _log(msg)
            return {
                "success": True,
                "total_articles": 0,
                "copied_articles": 0,
                "destinations": len(valid_dests),
                "cancelled": False,
            }

        skipped_incomplete = len(raw_articles) - total_articles
        extra_note = f" (skipped {skipped_incomplete} incomplete articles missing models)" if skipped_incomplete > 0 else ""
        _log(f"Found {total_articles} article(s) with finished models to copy{extra_note}.")

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
                target_dest_files = [
                    (dest if dest.name.lower() == "storage" else dest / "storage") / rel_file
                    for dest in valid_dests
                ]

                try:
                    bytes_written = _copy_stream_to_destinations(
                        src_file, target_dest_files, stop_event=stop_event
                    )
                    total_bytes_copied += bytes_written
                except Exception as fe:
                    _log(f"⚠️ Error copying file {src_file.name}: {fe}")

            # 5. Extract model zip files and delete zip on destination flash drives
            for dest in valid_dests:
                dest_storage = dest if dest.name.lower() == "storage" else dest / "storage"
                dest_article_dir = dest_storage / rel_folder
                dest_model_dir = dest_article_dir / "model"
                if dest_model_dir.is_dir():
                    for archive in list(dest_model_dir.iterdir()):
                        if not archive.is_file():
                            continue
                        if archive.suffix.lower() == ".zip":
                            try:
                                _log(f"  📦 Unzipping model archive on {dest.name}: {archive.name}...")
                                with zipfile.ZipFile(archive, "r") as zf:
                                    zf.extractall(dest_model_dir)
                                archive.unlink()
                                _log(f"  ✓ Extracted and deleted zip archive: {archive.name}")
                            except Exception as ze:
                                _log(f"  ⚠️ Could not extract zip {archive.name} on {dest.name}: {ze}")
                        elif archive.suffix.lower() in (".rar", ".7z"):
                            try:
                                shutil.unpack_archive(str(archive), str(dest_model_dir))
                                archive.unlink()
                                _log(f"  ✓ Extracted and deleted archive: {archive.name}")
                            except Exception:
                                pass

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
