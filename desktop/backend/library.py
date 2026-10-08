import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import requests
from bs4 import BeautifulSoup as bs

import config
from config import BASE_URL

logger = logging.getLogger("library")


def format_bytes(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.1f} {units[i]}"


MODEL_EXTS = {".zip", ".rar", ".7z", ".skp"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
UNSORTED = "Imported"


def _safe_name(name: str, limit: int = 80) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")[:limit].rstrip(" .") or UNSORTED


def _describe_error(e: Exception) -> str:
    """Short, user-facing reason for a failed file operation."""
    if isinstance(e, OSError) and (e.errno == 28 or getattr(e, "winerror", None) == 112):
        return "Disk is full"
    if isinstance(e, PermissionError):
        return "Permission denied"
    return (getattr(e, "strerror", None) or str(e))[:120]


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_article_directory(dir_path: Path) -> bool:
    """Checks if a directory directly represents an article folder."""
    if not dir_path.is_dir() or dir_path.name.startswith("."):
        return False
    if (dir_path / "model").is_dir() or (dir_path / "meta.json").is_file():
        return True
    has_subdirs = False
    for item in dir_path.iterdir():
        if item.is_file() and item.suffix.lower() in IMAGE_EXTS:
            return True
        if item.is_dir() and not item.name.startswith(".") and item.name != "model":
            has_subdirs = True
    # If it has no subdirectories, it's a leaf folder (hence an article directory)
    return not has_subdirs


class LibraryManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir_override = Path(base_dir) if base_dir else None

    @property
    def base_dir(self) -> Path:
        """Follows config.FEEDS_DIR so a storage-location change applies immediately."""
        d = self._base_dir_override or Path(config.FEEDS_DIR)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_meta(self, article_dir: Path) -> Dict[str, Any]:
        meta_file = article_dir / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_meta(self, article_dir: Path, data: Dict[str, Any]):
        meta_file = article_dir / "meta.json"
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save meta to %s: %s", meta_file, e)

    def find_article_url(
        self,
        article_title_or_dir: Union[str, Path],
        article_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Resolves the original CGTips article URL from meta.json or site search."""
        if isinstance(article_title_or_dir, Path):
            dir_path = article_title_or_dir
            title = dir_path.name
        else:
            title = str(article_title_or_dir)
            dir_path = article_dir or (self.base_dir / title)

        # 1. Check meta.json
        meta = self.get_meta(dir_path)
        if meta.get("article_url"):
            return meta["article_url"]

        # 2. Extract leading number if present (e.g. "19492. Free Sketchup...")
        match = re.match(r"^(\d+)", title)
        query = match.group(1) if match else title[:30]

        try:
            search_url = f"{BASE_URL}?s={requests.utils.quote(query)}"
            r = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                soup = bs(r.text, "html.parser")
                for a in soup.select("h2.entry-title a, h3.entry-title a, article a"):
                    href = a.get("href", "")
                    if match and match.group(1) in href:
                        meta["article_url"] = href
                        self.save_meta(dir_path, meta)
                        return href
                    elif not match and href.startswith(BASE_URL):
                        meta["article_url"] = href
                        self.save_meta(dir_path, meta)
                        return href
        except Exception as e:
            logger.debug("Failed querying site for article URL: %s", e)

        return None

    def find_article_url_on_site(self, article_dir: Path) -> Optional[str]:
        """Alias for find_article_url accepting article directory path."""
        return self.find_article_url(article_dir)

    def _extract_article_info(
        self,
        article_dir: Path,
        cat_name: str,
        sub_name: str,
    ) -> Dict[str, Any]:
        article_title = article_dir.name
        model_dir = article_dir / "model"

        model_file = None
        model_size = 0
        if model_dir.exists() and model_dir.is_dir():
            model_files = sorted(
                f for f in model_dir.iterdir()
                if f.is_file() and not f.name.startswith(".") and f.stat().st_size > 0
            )
            if model_files:
                model_file = model_files[0]
                model_size = model_file.stat().st_size

        # Natural sort images
        images = []
        raw_imgs = [
            img for img in article_dir.iterdir()
            if img.is_file() and img.suffix.lower() in IMAGE_EXTS
        ]

        def _sort_key(p: Path):
            m = re.search(r"(\d+)", p.stem)
            return int(m.group(1)) if m else 9999

        raw_imgs.sort(key=_sort_key)
        for img in raw_imgs:
            images.append(str(img.relative_to(self.base_dir)))

        rel_article = str(article_dir.relative_to(self.base_dir))
        rel_model = str(model_file.relative_to(self.base_dir)) if model_file else None
        meta = self.get_meta(article_dir)

        return {
            "id": rel_article,
            "category": cat_name,
            "subcategory": sub_name,
            "title": article_title.replace("_", " "),
            "folder_path": rel_article,
            "has_model": model_file is not None,
            "model_filename": model_file.name if model_file else None,
            "model_path": rel_model,
            "model_size": format_bytes(model_size),
            "model_size_bytes": model_size,
            "images": images,
            "images_count": len(images),
            "article_url": meta.get("article_url"),
            "imported": bool(meta.get("imported")),
            "modified_at": int(article_dir.stat().st_mtime),
            "_image_bytes": sum(i.stat().st_size for i in raw_imgs),
        }

    def _scan_article(self, article_dir: Path, cat_name: str, sub_name: str) -> Dict[str, Any]:
        return self._extract_article_info(article_dir, cat_name, sub_name)

    def scan_library(
        self,
        search: Optional[str] = None,
        category_filter: Optional[str] = None,
        subcategory_filter: Optional[str] = None,
        missing_only: bool = False,
    ) -> Dict[str, Any]:
        all_scanned: List[Dict[str, Any]] = []
        total_models = 0
        missing_models = 0
        total_images = 0
        total_size_bytes = 0
        categories_set = set()
        subcategories_map: Dict[str, set] = {}

        if not self.base_dir.exists():
            return {
                "items": [],
                "stats": {
                    "total_models": 0,
                    "missing_models": 0,
                    "total_images": 0,
                    "total_size": "0 B",
                    "total_size_bytes": 0,
                    "categories_count": 0,
                    "subcategories_count": 0,
                },
                "categories": [],
                "subcategories_hierarchy": {},
            }

        def _visible_dirs(d: Path):
            return [x for x in sorted(d.iterdir()) if x.is_dir() and not x.name.startswith(".")]

        # Categories are top-level subfolders in FEEDS_DIR
        for cat_dir in _visible_dirs(self.base_dir):
            cat_name = cat_dir.name
            categories_set.add(cat_name)
            if cat_name not in subcategories_map:
                subcategories_map[cat_name] = set()

            for sub_dir in _visible_dirs(cat_dir):
                # Check if sub_dir is an article folder directly (2-tier e.g. Direct_Downloads/Article)
                if is_article_directory(sub_dir):
                    sub_name = "General"
                    subcategories_map[cat_name].add(sub_name)
                    item = self._extract_article_info(sub_dir, cat_name, sub_name)
                    all_scanned.append(item)
                else:
                    # 3-tier: Category / Subcategory / Article
                    sub_name = sub_dir.name
                    subcategories_map[cat_name].add(sub_name)

                    for article_dir in _visible_dirs(sub_dir):
                        if article_dir.name == "model":
                            continue
                        item = self._extract_article_info(article_dir, cat_name, sub_name)
                        if item["has_model"] or item["images_count"] or item["article_url"]:
                            all_scanned.append(item)

        # Compute global stats from all scanned items
        for it in all_scanned:
            if it["has_model"]:
                total_models += 1
            else:
                missing_models += 1
            total_images += it["images_count"]
            total_size_bytes += it["model_size_bytes"] + it.get("_image_bytes", 0)

        # Filter items according to search, category, and missing_only
        items = []
        for it in all_scanned:
            if missing_only and it["has_model"]:
                continue
            if category_filter and category_filter != "all" and it["category"] != category_filter:
                continue
            if subcategory_filter and subcategory_filter != "all" and it["subcategory"] != subcategory_filter:
                continue
            if search:
                s_lower = search.lower()
                match_title = s_lower in it["title"].lower()
                match_cat = s_lower in it["category"].lower() or s_lower in it["subcategory"].lower()
                match_file = it["model_filename"] and s_lower in it["model_filename"].lower()
                if not (match_title or match_cat or match_file):
                    continue
            items.append(it)

        # Clean internal fields
        for it in all_scanned:
            it.pop("_image_bytes", None)

        # Sort items newest first
        items.sort(key=lambda x: x["modified_at"], reverse=True)

        hierarchy = {cat: sorted(list(subs)) for cat, subs in subcategories_map.items()}
        total_subcategories = sum(len(subs) for subs in subcategories_map.values())

        return {
            "items": items,
            "stats": {
                "total_models": total_models,
                "missing_models": missing_models,
                "total_images": total_images,
                "total_size": format_bytes(total_size_bytes),
                "total_size_bytes": total_size_bytes,
                "categories_count": len(categories_set),
                "subcategories_count": total_subcategories,
            },
            "categories": sorted(list(categories_set)),
            "subcategories_hierarchy": hierarchy,
        }

    def get_articles_by_scope(
        self,
        scope: str = "all",
        target: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves articles matching specified scope:
        scope: "article" | "subcategory" | "category" | "all"
        target:
          - for "article": folder_path
          - for "subcategory": {"category": ..., "subcategory": ...} or (category, subcategory)
          - for "category": category_name
        """
        all_items = self.scan_library().get("items", [])
        if scope == "article":
            folder = str(target).strip()
            return [it for it in all_items if it["folder_path"] == folder or it["id"] == folder]
        elif scope == "subcategory":
            if isinstance(target, dict):
                c = target.get("category", "")
                s = target.get("subcategory", "")
            elif isinstance(target, (list, tuple)) and len(target) >= 2:
                c, s = target[0], target[1]
            else:
                c, s = "", ""
            return [it for it in all_items if it["category"] == c and it["subcategory"] == s]
        elif scope == "category":
            cat_name = str(target).strip()
            return [it for it in all_items if it["category"] == cat_name]
        return all_items

    def get_missing_items(
        self,
        scope: str = "all",
        target: Any = None,
    ) -> List[Dict[str, Any]]:
        """Returns articles matching the scope that are missing model files."""
        articles = self.get_articles_by_scope(scope=scope, target=target)
        return [it for it in articles if not it.get("has_model")]

    def delete_item(self, rel_folder_path: str) -> bool:
        """Safely removes an article folder within FEEDS_DIR."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not _is_within(target, self.base_dir):
            raise ValueError("Invalid target path outside feeds directory")

        if target.exists() and target.is_dir():
            shutil.rmtree(target)
            return True
        return False

    def clear_library(self, mode: str = "all", category: Optional[str] = None) -> int:
        """
        Clears items from the library based on mode.
        mode:
          - "all": Deletes all article directories in FEEDS_DIR.
          - "missing": Deletes only article folders where has_model == False.
          - "category": Deletes all articles in a specific category.
        Returns the count of deleted article folders.
        """
        items = self.scan_library().get("items", [])
        to_delete = []

        if mode == "all":
            to_delete = items
        elif mode == "missing":
            to_delete = [it for it in items if not it["has_model"]]
        elif mode == "category" and category:
            to_delete = [it for it in items if it["category"] == category]

        deleted_count = 0
        for it in to_delete:
            folder = it.get("folder_path")
            if folder:
                try:
                    if self.delete_item(folder):
                        deleted_count += 1
                except Exception as e:
                    logger.warning("Error deleting folder %s: %s", folder, e)

        # Clean up any leftover empty subdirectories
        try:
            for cat_dir in self.base_dir.iterdir():
                if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                    for sub_dir in cat_dir.iterdir():
                        if sub_dir.is_dir() and not any(sub_dir.iterdir()):
                            sub_dir.rmdir()
                    if not any(cat_dir.iterdir()):
                        cat_dir.rmdir()
        except Exception:
            pass

        return deleted_count

    # --- Importing existing downloads ---

    def _discover_articles(self, root: Path, log_cb=None) -> List[Dict[str, Any]]:
        """
        Finds importable articles under `root`. Understood layouts:
          * <article>/model/<archive> + images        (this app's own layout)
          * <folder>/<one archive> + images            (one article per folder)
          * <folder>/<many archives>                   (each archive is an article;
                                                        images sharing its name go along)
        Category / sub-category come from the two folders above the article when
        they exist, otherwise "Imported".
        """
        found: List[Dict[str, Any]] = []
        chain_root = [root.name] if root.name else []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            d = Path(dirpath)
            if d.name == "model" and d != root:
                continue  # handled by the parent article
            files = [d / f for f in sorted(filenames) if not f.startswith(".")]
            models_here = [f for f in files if f.suffix.lower() in MODEL_EXTS]
            images_here = [f for f in files if f.suffix.lower() in IMAGE_EXTS]
            chain = chain_root + list(d.relative_to(root).parts)

            model_sub = d / "model"
            sub_models = (
                [f for f in sorted(model_sub.iterdir()) if f.is_file() and f.suffix.lower() in MODEL_EXTS]
                if model_sub.is_dir() else []
            )

            if sub_models or len(models_here) == 1:
                found.append({"name": d.name, "parents": chain[:-1], "models": sub_models or models_here, "images": images_here})
            elif len(models_here) > 1:
                for m in models_here:
                    imgs = [i for i in images_here if i.stem.startswith(m.stem)]
                    found.append({"name": m.stem, "parents": chain, "models": [m], "images": imgs})
        return found

    def _import_article(self, art: Dict[str, Any], move: bool) -> str:
        """Copies/moves one discovered article into the library. Returns 'imported' or 'skipped'."""
        parents = art["parents"]
        category = _safe_name(parents[-2]) if len(parents) >= 2 else UNSORTED
        sub = _safe_name(parents[-1]) if len(parents) >= 1 else UNSORTED
        dest = self.base_dir / category / sub / _safe_name(art["name"])
        model_dir = dest / "model"
        dest_existed = dest.exists()
        model_dir.mkdir(parents=True, exist_ok=True)

        transfer = shutil.move if move else shutil.copy2
        changed = False
        created: List[Path] = []

        try:
            for m in art["models"]:
                target = model_dir / m.name
                if target.exists() and target.stat().st_size == m.stat().st_size:
                    continue
                created.append(target)
                transfer(str(m), str(target))
                changed = True

            existing_imgs = [i for i in dest.iterdir() if i.is_file() and i.suffix.lower() in IMAGE_EXTS]
            existing_sizes = {i.stat().st_size for i in existing_imgs}
            n = len(existing_imgs)
            for img in art["images"]:
                if img.stat().st_size in existing_sizes:
                    continue  # same picture already imported
                n += 1
                while (dest / f"image_{n}{img.suffix.lower()}").exists():
                    n += 1
                created.append(dest / f"image_{n}{img.suffix.lower()}")
                transfer(str(img), str(created[-1]))
                changed = True

            if n == 0:
                created.extend(self._extract_zip_previews(model_dir, dest))
                changed = changed or bool(created)
        except Exception:
            if not move:
                for f in created:
                    try:
                        f.unlink(missing_ok=True)
                    except OSError:
                        pass
            if not dest_existed:
                shutil.rmtree(dest, ignore_errors=True)
            else:
                try:
                    model_dir.rmdir()
                except OSError:
                    pass
            raise

        if changed:
            meta = self.get_meta(dest)
            meta.setdefault("imported", True)
            meta.setdefault("title", art["name"])
            self.save_meta(dest, meta)
        return "imported" if changed else "skipped"

    def _extract_zip_previews(self, model_dir: Path, dest: Path, limit: int = 4) -> List[Path]:
        """Pulls preview pictures out of a .zip model when no images came with it."""
        out: List[Path] = []
        for archive in sorted(model_dir.glob("*.zip")):
            try:
                with zipfile.ZipFile(archive) as zf:
                    pics = [i for i in zf.infolist()
                            if not i.is_dir() and Path(i.filename).suffix.lower() in IMAGE_EXTS
                            and 0 < i.file_size < 20 * 1024 * 1024]
                    pics.sort(key=lambda i: i.file_size, reverse=True)
                    for info in pics[:limit]:
                        target = dest / f"image_{len(out) + 1}{Path(info.filename).suffix.lower()}"
                        with zf.open(info) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        out.append(target)
            except zipfile.BadZipFile:
                continue
            if out:
                break
        return out

    def import_paths(
        self,
        paths: List[str],
        move: bool = False,
        log_cb: Optional[Any] = None,
        progress_cb: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Imports already-downloaded model archives/images (files or folders) into the library."""
        base = self.base_dir
        arts: List[Dict[str, Any]] = []
        loose: Dict[Path, List[Path]] = {}
        notes: List[str] = []

        for raw in paths:
            p = Path(raw).expanduser()
            if not p.exists():
                notes.append(f"Not found: {p}")
                continue
            if p.is_dir():
                if _is_within(p, base):
                    notes.append(f"Already in the library folder: {p}")
                    continue
                arts.extend(self._discover_articles(p, log_cb))
            elif p.suffix.lower() in MODEL_EXTS | IMAGE_EXTS:
                loose.setdefault(p.parent, []).append(p)

        for parent, files in loose.items():
            if _is_within(parent, base):
                notes.append(f"Already in the library folder: {parent}")
                continue
            images = [f for f in files if f.suffix.lower() in IMAGE_EXTS]
            for m in (f for f in files if f.suffix.lower() in MODEL_EXTS):
                arts.append({
                    "name": m.stem, "parents": [], "models": [m],
                    "images": [i for i in images if i.stem.startswith(m.stem)],
                })

        stats = {"found": len(arts), "imported": 0, "skipped": 0, "failed": 0, "notes": notes, "errors": []}

        needed = sum(
            f.stat().st_size
            for art in arts for f in art["models"] + art["images"]
            if not move or f.anchor.lower() != base.anchor.lower()
        )
        free = shutil.disk_usage(base).free
        if needed > free:
            raise OSError(
                f"Not enough disk space: the import needs {format_bytes(needed)} but only "
                f"{format_bytes(free)} is free on {base.anchor}. Free some space or change the "
                f"storage location in Settings."
            )

        for idx, art in enumerate(arts, 1):
            try:
                outcome = self._import_article(art, move)
                stats[outcome] += 1
                if log_cb:
                    log_cb(f"{outcome.capitalize()}: {art['name'][:70]}")
            except Exception as e:
                stats["failed"] += 1
                reason = _describe_error(e)
                if reason not in stats["errors"]:
                    stats["errors"].append(reason)
                logger.warning("Import failed for %s: %s", art["name"], e)
                if log_cb:
                    log_cb(f"Failed: {art['name'][:60]} ({reason})")
            if progress_cb:
                progress_cb(idx, len(arts))
        return stats

    def create_images_zip(self, rel_folder_path: str) -> Path:
        """Packages all images of an article into a temporary zip file."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not _is_within(target, self.base_dir):
            raise ValueError("Invalid target path")

        temp_dir = Path(tempfile.gettempdir()) / "cgtips_exports"
        temp_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", target.name)[:50]
        zip_path = temp_dir / f"{safe_name}_images.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for img in sorted(target.iterdir()):
                if img.is_file() and img.suffix.lower() in IMAGE_EXTS:
                    zf.write(img, arcname=img.name)

        return zip_path

    def create_bundle_zip(self, rel_folder_path: str) -> Path:
        """Packages both the model archive and all images of an article into a zip."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not _is_within(target, self.base_dir):
            raise ValueError("Invalid target path")

        temp_dir = Path(tempfile.gettempdir()) / "cgtips_exports"
        temp_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", target.name)[:50]
        zip_path = temp_dir / f"{safe_name}_bundle.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(target.rglob("*")):
                if item.is_file() and not item.name.startswith("."):
                    arcname = item.relative_to(target)
                    zf.write(item, arcname=str(arcname))

        return zip_path

    def create_bulk_zip(self, rel_folder_paths: List[str], export_type: str = "both") -> Path:
        """Creates a bulk zip containing multiple articles."""
        temp_dir = Path(tempfile.gettempdir()) / "cgtips_exports"
        temp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = temp_dir / f"cgtips_bulk_{export_type}_{os.getpid()}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path in rel_folder_paths:
                target = (self.base_dir / rel_path).resolve()
                if not _is_within(target, self.base_dir) or not target.exists():
                    continue

                folder_prefix = target.name
                if export_type in ("images", "both"):
                    for img in target.iterdir():
                        if img.is_file() and img.suffix.lower() in IMAGE_EXTS:
                            zf.write(img, arcname=f"{folder_prefix}/images/{img.name}")

                if export_type in ("models", "both"):
                    model_dir = target / "model"
                    if model_dir.exists():
                        for m in model_dir.iterdir():
                            if m.is_file() and not m.name.startswith("."):
                                zf.write(m, arcname=f"{folder_prefix}/model/{m.name}")

        return zip_path


library_manager = LibraryManager()
