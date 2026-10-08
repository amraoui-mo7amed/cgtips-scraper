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

from config import FEEDS_DIR, BASE_URL

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


def is_article_directory(dir_path: Path) -> bool:
    """Checks if a directory directly represents an article folder."""
    if not dir_path.is_dir() or dir_path.name.startswith("."):
        return False
    if (dir_path / "model").is_dir() or (dir_path / "meta.json").is_file():
        return True
    has_subdirs = False
    for item in dir_path.iterdir():
        if item.is_file() and item.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return True
        if item.is_dir() and not item.name.startswith(".") and item.name != "model":
            has_subdirs = True
    # If it has no subdirectories, it's a leaf folder (hence an article directory)
    return not has_subdirs


class LibraryManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or FEEDS_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

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
            model_files = [f for f in model_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
            if model_files:
                model_file = model_files[0]
                model_size = model_file.stat().st_size

        # Natural sort images
        images = []
        raw_imgs = [
            img for img in article_dir.iterdir()
            if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
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
            "modified_at": int(article_dir.stat().st_mtime),
        }

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

        # Categories are top-level subfolders in FEEDS_DIR
        for cat_dir in sorted(self.base_dir.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue

            cat_name = cat_dir.name
            categories_set.add(cat_name)
            if cat_name not in subcategories_map:
                subcategories_map[cat_name] = set()

            for sub_dir in sorted(cat_dir.iterdir()):
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue

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

                    for article_dir in sorted(sub_dir.iterdir()):
                        if not article_dir.is_dir() or article_dir.name.startswith("."):
                            continue
                        item = self._extract_article_info(article_dir, cat_name, sub_name)
                        all_scanned.append(item)

        # Compute global stats from all scanned items
        for it in all_scanned:
            if it["has_model"]:
                total_models += 1
            else:
                missing_models += 1
            total_images += it["images_count"]
            total_size_bytes += it["model_size_bytes"]
            # Add image file sizes
            art_dir = self.base_dir / it["folder_path"]
            for img_rel in it["images"]:
                img_path = self.base_dir / img_rel
                if img_path.exists():
                    total_size_bytes += img_path.stat().st_size

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

    def _accumulate_item(
        self,
        item: Dict[str, Any],
        items: List[Dict[str, Any]],
        search: Optional[str],
        category_filter: Optional[str],
        subcategory_filter: Optional[str],
    ):
        if category_filter and category_filter != "all" and item["category"] != category_filter:
            return
        if subcategory_filter and subcategory_filter != "all" and item["subcategory"] != subcategory_filter:
            return

        if search:
            s_lower = search.lower()
            match_title = s_lower in item["title"].lower()
            match_cat = s_lower in item["category"].lower() or s_lower in item["subcategory"].lower()
            match_file = item["model_filename"] and s_lower in item["model_filename"].lower()
            if not (match_title or match_cat or match_file):
                return

        items.append(item)

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
        if not str(target).startswith(str(self.base_dir.resolve())):
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

    def create_images_zip(self, rel_folder_path: str) -> Path:
        """Packages all images of an article into a temporary zip file."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not str(target).startswith(str(self.base_dir.resolve())):
            raise ValueError("Invalid target path")

        temp_dir = Path(tempfile.gettempdir()) / "cgtips_exports"
        temp_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", target.name)[:50]
        zip_path = temp_dir / f"{safe_name}_images.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for img in sorted(target.iterdir()):
                if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    zf.write(img, arcname=img.name)

        return zip_path

    def create_bundle_zip(self, rel_folder_path: str) -> Path:
        """Packages both the model archive and all images of an article into a zip."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not str(target).startswith(str(self.base_dir.resolve())):
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
                if not str(target).startswith(str(self.base_dir.resolve())) or not target.exists():
                    continue

                folder_prefix = target.name
                if export_type in ("images", "both"):
                    for img in target.iterdir():
                        if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                            zf.write(img, arcname=f"{folder_prefix}/images/{img.name}")

                if export_type in ("models", "both"):
                    model_dir = target / "model"
                    if model_dir.exists():
                        for m in model_dir.iterdir():
                            if m.is_file() and not m.name.startswith("."):
                                zf.write(m, arcname=f"{folder_prefix}/model/{m.name}")

        return zip_path


library_manager = LibraryManager()
