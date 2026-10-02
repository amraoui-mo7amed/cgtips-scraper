"""
Download history: the articles whose model has already been downloaded, kept
independently of the files themselves.

It lets another machine skip articles that were downloaded elsewhere (the
models don't have to be copied over), and is filled automatically whenever a
model download succeeds. Stored in data/download_history.json as
    {"version": 1, "articles": {"<key>": {"title", "link", "category", "subcategory", "added"}}}
where <key> is the article URL, or "t:<title key>" when no URL is known.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import config

logger = logging.getLogger("history")

_lock = threading.RLock()
_cache: Optional[Dict[str, Dict[str, Any]]] = None
_titles: Dict[str, str] = {}  # title key -> record key, so URL records also match by title


def history_file() -> Path:
    return Path(config.DATA_DIR) / "download_history.json"


def title_key(title: str) -> str:
    # ASCII letters/digits only: old files carry mojibake ("â€“") where the site has "–",
    # and folder names are truncated, so compare a normalised prefix.
    return "t:" + "".join(ch for ch in (title or "").lower() if ch.isascii() and ch.isalnum())[:60]


def _url_key(link: str) -> str:
    return (link or "").strip().rstrip("/")


def _load() -> Dict[str, Dict[str, Any]]:
    global _cache, _titles
    if _cache is None:
        try:
            data = json.loads(history_file().read_text(encoding="utf-8"))
            _cache = dict(data.get("articles", {}))
        except FileNotFoundError:
            _cache = {}
        except Exception as e:
            logger.warning("Could not read download history: %s", e)
            _cache = {}
        _titles = {title_key(r.get("title", "")): k for k, r in _cache.items() if r.get("title")}
    return _cache


def _save():
    f = history_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "articles": _cache}, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _find(link: str, title: str) -> Optional[str]:
    h = _load()
    if link and _url_key(link) in h:
        return _url_key(link)
    if title:
        tk = title_key(title)
        if tk in h:
            return tk
        if tk != "t:" and tk in _titles:
            return _titles[tk]
    return None


def has(link: str = "", title: str = "") -> bool:
    with _lock:
        return _find(link, title) is not None


def count() -> int:
    with _lock:
        return len(_load())


def add_many(entries: Iterable[Dict[str, Any]]) -> int:
    """Records downloaded articles ({title, link, category, subcategory}). Returns how many were new."""
    entries = list(entries)
    added = 0
    with _lock:
        h = _load()
        now = time.strftime("%Y-%m-%d")
        for e in entries:
            link, title = _url_key(e.get("link") or ""), e.get("title") or ""
            if not link and title_key(title) == "t:":
                continue
            existing = _find(link, title)
            key = link or existing or title_key(title)
            if existing is None:
                added += 1
            rec = {"title": title, "link": link, "category": e.get("category", ""),
                   "subcategory": e.get("subcategory", ""), "added": now}
            merged = {**h.get(existing, {}), **{k: v for k, v in rec.items() if v}} if existing else rec
            if existing and existing != key:
                h.pop(existing, None)  # a title-only record now has its URL
            h[key] = merged
            if merged.get("title"):
                _titles[title_key(merged["title"])] = key
        if entries:
            _save()
    return added


def add(link: str, title: str, category: str = "", subcategory: str = "") -> None:
    add_many([{"link": link, "title": title, "category": category, "subcategory": subcategory}])


def export_to(path: str) -> int:
    with _lock:
        h = _load()
        Path(path).write_text(json.dumps({"version": 1, "articles": h}, ensure_ascii=False, indent=1), encoding="utf-8")
        return len(h)


def _model_on_disk(folder: Path) -> bool:
    model_dir = folder / "model"
    return model_dir.is_dir() and any(
        f.is_file() and not f.name.startswith(".") and f.stat().st_size > 0 for f in model_dir.iterdir()
    )


def import_from(path: str) -> Dict[str, int]:
    """
    Merges a history file into this one. Also understands the old scraper's
    selected_feeds.json: an entry counts as downloaded when it records a model
    file, or when its article folder (next to the json) still has the model.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = []
    found = 0
    if isinstance(data, dict) and "articles" in data:
        for rec in data["articles"].values():
            found += 1
            entries.append(rec)
    elif isinstance(data, dict) and "selected" in data:
        root = p.parent
        for sel in data.get("selected", []):
            for e in sel.get("feed_entries", []) or []:
                found += 1
                model_file = e.get("model_file")
                on_disk = False
                if not model_file:
                    imgs = e.get("downloaded_images") or []
                    if imgs:
                        on_disk = _model_on_disk((root / imgs[0]).parent)
                if model_file or on_disk:
                    entries.append({"title": e.get("title", ""), "link": e.get("link", ""),
                                    "subcategory": sel.get("name", "")})
    else:
        raise ValueError("Not a download history or feeds file")
    added = add_many(entries)
    return {"found": found, "downloaded": len(entries), "added": added, "total": count()}
