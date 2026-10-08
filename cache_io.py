"""
Export / import of the scraper cache so it can be moved between machines or
restored after a reinstall without re-fetching everything.

A cache archive is a plain zip containing:
    manifest.json          - metadata (format version, creation time, counts)
    categories.json        - scraped category taxonomy
    selected_feeds.json    - last feed session (entries, image/model state)
    download_history.json  - articles already downloaded (skipped by bulk downloads)
    cache/images/<md5>.img - cached thumbnails
"""

import json
import logging
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import config
import history

logger = logging.getLogger("cache_io")

FORMAT_VERSION = 1
_IMAGE_ENTRY = re.compile(r"^cache/images/[0-9a-f]{32}\.img$")
_MAX_JSON_BYTES = 64 * 1024 * 1024
_MAX_IMAGE_BYTES = 50 * 1024 * 1024


def _json_targets() -> Dict[str, Path]:
    return {
        "categories.json": Path(config.CATEGORIES_FILE),
        "selected_feeds.json": Path(config.SELECTED_FEEDS_FILE),
        "download_history.json": history.history_file(),
    }


def export_cache(
    dest_zip: str,
    include_images: bool = True,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Writes the cache archive to dest_zip. Returns a summary dict."""
    dest = Path(dest_zip)
    dest.parent.mkdir(parents=True, exist_ok=True)

    json_files = {name: p for name, p in _json_targets().items() if p.exists()}
    images = sorted(config.IMAGE_CACHE_DIR.glob("*.img")) if include_images and config.IMAGE_CACHE_DIR.exists() else []

    total = len(json_files) + len(images)
    done = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "format": FORMAT_VERSION,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "json_files": sorted(json_files),
            "images": len(images),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, path in json_files.items():
            zf.write(path, arcname=name)
            done += 1
            if progress_cb:
                progress_cb(done, total)
        for img in images:
            # Thumbnails are already compressed; store them as-is.
            zf.write(img, arcname=f"cache/images/{img.name}", compress_type=zipfile.ZIP_STORED)
            done += 1
            if progress_cb and (done % 50 == 0 or done == total):
                progress_cb(done, total)

    return {
        "path": str(dest),
        "json_files": sorted(json_files),
        "images": len(images),
        "size_bytes": dest.stat().st_size,
    }


def import_cache(
    src_zip: str,
    overwrite: bool = True,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """
    Restores a cache archive. Only known entries are extracted (no arbitrary
    paths), JSON is validated before it replaces the current file, and
    thumbnails already on disk are kept unless overwrite is set.
    """
    src = Path(src_zip)
    if not src.is_file() or not zipfile.is_zipfile(src):
        raise ValueError("Not a valid cache archive (zip file expected)")

    targets = _json_targets()
    restored_json = []
    images_added = 0
    images_skipped = 0

    with zipfile.ZipFile(src) as zf:
        infos = {i.filename: i for i in zf.infolist() if not i.is_dir()}
        known = [n for n in infos if n in targets or _IMAGE_ENTRY.match(n)]
        if not known:
            raise ValueError("Archive does not contain any CGTips cache data")

        done = 0
        total = len(known)

        for name, dest in targets.items():
            info = infos.get(name)
            if info is None:
                continue
            if info.file_size > _MAX_JSON_BYTES:
                raise ValueError(f"{name} is unreasonably large")
            data = json.loads(zf.read(info).decode("utf-8"))
            expected = list if name == "categories.json" else dict
            if not isinstance(data, expected):
                raise ValueError(f"{name} has an unexpected structure")
            if name == "download_history.json":
                # Merge rather than replace, so this machine's own history is kept.
                tmp = dest.with_suffix(".import.tmp")
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                try:
                    history.import_from(str(tmp))
                finally:
                    tmp.unlink(missing_ok=True)
                restored_json.append(name)
                done += 1
                continue
            if dest.exists() and not overwrite:
                done += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
            tmp.replace(dest)
            restored_json.append(name)
            done += 1
            if progress_cb:
                progress_cb(done, total)

        config.IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for name, info in infos.items():
            if not _IMAGE_ENTRY.match(name):
                continue
            target = config.IMAGE_CACHE_DIR / Path(name).name
            done += 1
            if info.file_size > _MAX_IMAGE_BYTES or (target.exists() and not overwrite):
                images_skipped += 1
                continue
            with zf.open(info) as r, open(target, "wb") as w:
                w.write(r.read())
            images_added += 1
            if progress_cb and (done % 50 == 0 or done == total):
                progress_cb(done, total)

    return {
        "json_files": restored_json,
        "images_added": images_added,
        "images_skipped": images_skipped,
    }
