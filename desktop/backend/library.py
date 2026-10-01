import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
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

    def find_article_url(self, article_title: str, article_dir: Path) -> Optional[str]:
        # 1. Check meta.json
        meta = self.get_meta(article_dir)
        if meta.get("article_url"):
            return meta["article_url"]

        # 2. Extract leading number if present (e.g. "19492. Free Sketchup...")
        match = re.match(r"^(\d+)", article_title)
        query = match.group(1) if match else article_title[:30]

        try:
            search_url = f"{BASE_URL}?s={query}"
            r = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                soup = bs(r.text, "html.parser")
                for a in soup.select("h2.entry-title a, h3.entry-title a, article a"):
                    href = a.get("href", "")
                    if match and match.group(1) in href:
                        meta["article_url"] = href
                        self.save_meta(article_dir, meta)
                        return href
                    elif not match and href.startswith(BASE_URL):
                        meta["article_url"] = href
                        self.save_meta(article_dir, meta)
                        return href
        except Exception as e:
            logger.debug("Failed querying site for article URL: %s", e)

        return None

    def scan_library(self, search: Optional[str] = None, category_filter: Optional[str] = None) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        total_models = 0
        total_images = 0
        total_size_bytes = 0
        categories_set = set()
        subcategories_set = set()

        if not self.base_dir.exists():
            return {
                "items": [],
                "stats": {
                    "total_models": 0,
                    "total_images": 0,
                    "total_size": "0 B",
                    "total_size_bytes": 0,
                    "categories_count": 0,
                    "subcategories_count": 0,
                },
                "categories": [],
            }

        # Categories are top-level subfolders in FEEDS_DIR
        for cat_dir in sorted(self.base_dir.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue

            cat_name = cat_dir.name
            categories_set.add(cat_name)

            for sub_dir in sorted(cat_dir.iterdir()):
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue

                sub_name = sub_dir.name
                subcategories_set.add(sub_name)

                # Direct downloads or articles
                for article_dir in sorted(sub_dir.iterdir()):
                    if not article_dir.is_dir() or article_dir.name.startswith("."):
                        continue

                    article_title = article_dir.name
                    model_dir = article_dir / "model"

                    model_file = None
                    model_size = 0
                    if model_dir.exists() and model_dir.is_dir():
                        model_files = [f for f in model_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
                        if model_files:
                            model_file = model_files[0]
                            model_size = model_file.stat().st_size
                            total_models += 1
                            total_size_bytes += model_size

                    # Find preview images (sorted naturally: image_1, image_2, image_10)
                    images = []
                    raw_imgs = [img for img in article_dir.iterdir() if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
                    
                    def _sort_key(p: Path):
                        m = re.search(r"(\d+)", p.stem)
                        return int(m.group(1)) if m else 9999

                    raw_imgs.sort(key=_sort_key)
                    for img in raw_imgs:
                        images.append(str(img.relative_to(self.base_dir)))
                        total_images += 1
                        total_size_bytes += img.stat().st_size

                    # Filters
                    if category_filter and category_filter != "all" and cat_name != category_filter:
                        continue

                    if search:
                        s_lower = search.lower()
                        match_title = s_lower in article_title.lower()
                        match_cat = s_lower in cat_name.lower() or s_lower in sub_name.lower()
                        match_file = model_file and s_lower in model_file.name.lower()
                        if not (match_title or match_cat or match_file):
                            continue

                    rel_article = str(article_dir.relative_to(self.base_dir))
                    rel_model = str(model_file.relative_to(self.base_dir)) if model_file else None
                    meta = self.get_meta(article_dir)

                    items.append({
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
                    })

        # Sort items newest first
        items.sort(key=lambda x: x["modified_at"], reverse=True)

        return {
            "items": items,
            "stats": {
                "total_models": total_models,
                "total_images": total_images,
                "total_size": format_bytes(total_size_bytes),
                "total_size_bytes": total_size_bytes,
                "categories_count": len(categories_set),
                "subcategories_count": len(subcategories_set),
            },
            "categories": sorted(list(categories_set)),
        }

    def delete_item(self, rel_folder_path: str) -> bool:
        """Safely removes an article folder within FEEDS_DIR."""
        target = (self.base_dir / rel_folder_path).resolve()
        if not str(target).startswith(str(self.base_dir.resolve())):
            raise ValueError("Invalid target path outside feeds directory")

        if target.exists() and target.is_dir():
            shutil.rmtree(target)
            return True
        return False

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
        """
        Creates a bulk zip containing multiple articles.
        export_type: "images", "models", or "both"
        """
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
