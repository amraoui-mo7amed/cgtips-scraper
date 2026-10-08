import os
import shutil
import tempfile
import unittest
from pathlib import Path

import config
import history
from download_queue import DownloadQueue
from cache_io import export_cache, import_cache


class TestBulkAndQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cgtips_test_queue_")
        self.old_data_dir = config.DATA_DIR
        self.old_feeds_dir = config.FEEDS_DIR
        self.old_cache = history._cache
        self.old_titles = history._titles
        history._cache = None
        history._titles = {}

        config.DATA_DIR = Path(self.temp_dir) / "data"
        config.FEEDS_DIR = Path(self.temp_dir) / "feeds"
        config.CATEGORIES_FILE = str(config.FEEDS_DIR / "categories.json")
        config.SELECTED_FEEDS_FILE = str(config.FEEDS_DIR / "selected_feeds.json")
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.FEEDS_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        config.DATA_DIR = self.old_data_dir
        config.FEEDS_DIR = self.old_feeds_dir
        config.CATEGORIES_FILE = str(config.FEEDS_DIR / "categories.json")
        config.SELECTED_FEEDS_FILE = str(config.FEEDS_DIR / "selected_feeds.json")
        history._cache = self.old_cache
        history._titles = self.old_titles
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_history_tracker(self):
        self.assertFalse(history.has(link="https://example.com/test-article"))
        self.assertEqual(history.count(), 0)

        history.add(
            link="https://example.com/test-article",
            title="Modern Sofa 3D",
            category="Furniture",
            subcategory="Sofa",
        )

        self.assertTrue(history.has(link="https://example.com/test-article"))
        self.assertTrue(history.has(title="Modern Sofa 3D"))
        self.assertEqual(history.count(), 1)

        # Export and import
        export_path = Path(self.temp_dir) / "history_export.json"
        exported = history.export_to(str(export_path))
        self.assertEqual(exported, 1)

        history._cache = None
        history._titles = {}
        # Clean history file
        if history.history_file().exists():
            history.history_file().unlink()

        self.assertEqual(history.count(), 0)
        res = history.import_from(str(export_path))
        self.assertEqual(res["added"], 1)
        self.assertEqual(history.count(), 1)
        self.assertTrue(history.has(link="https://example.com/test-article"))

    def test_download_queue_operations(self):
        queue = DownloadQueue()
        self.assertEqual(len(queue.items()), 0)

        test_articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/1",
            },
            {
                "title": "Article 2",
                "link": "https://example.com/2",
            },
            {
                "title": "Article 3",
                "link": "https://example.com/3",
            },
        ]

        added = queue.add_articles(
            test_articles,
            category="Architecture",
            subcategory="Villa",
            models=True,
            images=True,
            start=False,
        )
        self.assertEqual(added, 3)
        self.assertEqual(len(queue.items()), 3)

        stats = queue.stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["pending"], 3)

        # Test move to top
        items = queue.items()
        last_id = items[2]["id"]
        queue.move_to_top(last_id)
        self.assertEqual(queue.items()[0]["id"], last_id)

        # Test remove
        queue.remove(last_id)
        self.assertEqual(len(queue.items()), 2)

        # Test clear_all
        cleared = queue.clear_all()
        self.assertEqual(cleared, 2)
        self.assertEqual(len(queue.items()), 0)
        self.assertEqual(queue.stats()["total"], 0)

        # Test no_model handling
        queue.add_articles(
            [{"title": "Article No Model", "link": "https://example.com/no-model"}],
            category="Furniture",
            subcategory="Cabinets",
            models=True,
            images=True,
            start=False,
        )
        self.assertEqual(len(queue.items()), 1)
        item = queue.items()[0]
        # Simulate finishing with no_model
        queue._finish(item, "no_model", "Model download failed (Drive quota or file unreachable)")
        stats = queue.stats()
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["no_model"], 1)

        # Test retry_no_model
        retried = queue.retry_no_model()
        self.assertEqual(retried, 1)
        self.assertEqual(queue.items()[0]["status"], "pending")

        # Test clear_no_model
        queue._finish(queue.items()[0], "no_model", "No download link found")
        cleared_no_mod = queue.clear_no_model()
        self.assertEqual(cleared_no_mod, 1)
        self.assertEqual(len(queue.items()), 0)

    def test_cache_export_import(self):
        # Create a mock categories.json file (must be a JSON array)
        feed_file = Path(config.CATEGORIES_FILE)
        feed_file.write_text('[{"name": "Architecture", "subcategories": []}]', encoding="utf-8")

        export_zip = Path(self.temp_dir) / "cache_export.zip"
        res = export_cache(str(export_zip), include_images=False)
        self.assertIn("categories.json", res.get("json_files", []))
        self.assertTrue(export_zip.exists())

        # Wipe feeds_dir and import
        feed_file.unlink()
        self.assertFalse(feed_file.exists())

        imported = import_cache(str(export_zip))
        self.assertIn("categories.json", imported.get("json_files", []))
        self.assertTrue(feed_file.exists())


if __name__ == "__main__":
    unittest.main()
