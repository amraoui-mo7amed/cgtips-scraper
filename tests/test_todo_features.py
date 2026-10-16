"""
Unit and integration tests for features specified in TODO.md:
1. Re-download missing models (by article, by category, by subcategory, all at once)
2. Clear download list (all vs missing only)
3. Copy articles files (by article, by category, by subcategory) with client agent auto-copy and multi-destination disks
4. Settings Manager for client agent and destination disks
"""

import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from desktop.backend.settings_manager import SettingsManager
from desktop.backend.library import LibraryManager
from desktop.backend.copy_manager import CopyManager
from desktop.backend.batch_downloader import batch_download_missing
from desktop.backend.upload_manager import UploadManager


class TestTodoFeatures(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="cgtips_test_"))
        self.feeds_dir = self.temp_dir / "feeds"
        self.feeds_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.temp_dir / "settings.json"
        self.settings = SettingsManager(settings_file=self.settings_file)
        self.library = LibraryManager(base_dir=self.feeds_dir)

        # Create dummy client agent executable
        self.client_agent_file = self.temp_dir / "client_agent.exe"
        self.client_agent_file.write_bytes(b"MZ_DUMMY_CLIENT_AGENT_BINARY_EXE")

        # Create mock categories, subcategories, and articles
        # Category: Architecture -> Subcategory: Houses -> Article 1 (has model)
        art1 = self.feeds_dir / "Architecture" / "Houses" / "101. Modern Villa"
        art1.mkdir(parents=True, exist_ok=True)
        (art1 / "image_1.jpg").write_bytes(b"image1")
        (art1 / "model").mkdir(exist_ok=True)
        with zipfile.ZipFile(art1 / "model" / "villa.zip", "w") as zf:
            zf.writestr("villa.skp", b"dummy_model_skp_bytes")

        # Category: Architecture -> Subcategory: Houses -> Article 2 (missing model)
        art2 = self.feeds_dir / "Architecture" / "Houses" / "102. Wooden Cabin"
        art2.mkdir(parents=True, exist_ok=True)
        (art2 / "image_1.jpg").write_bytes(b"image2")

        # Category: Architecture -> Subcategory: Towers -> Article 3 (missing model)
        art3 = self.feeds_dir / "Architecture" / "Towers" / "103. Glass Skyscraper"
        art3.mkdir(parents=True, exist_ok=True)
        (art3 / "image_1.jpg").write_bytes(b"image3")

        # Category: Direct_Downloads (2-tier) -> Article 4 (missing model)
        art4 = self.feeds_dir / "Direct_Downloads" / "104. Leather Couch"
        art4.mkdir(parents=True, exist_ok=True)
        (art4 / "image_1.jpg").write_bytes(b"image4")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_settings_manager(self):
        # 1. Test client agent path
        self.assertEqual(self.settings.get_client_agent_path(), "")
        self.settings.set_client_agent_path(str(self.client_agent_file))
        self.assertEqual(self.settings.get_client_agent_path(), str(self.client_agent_file))

        # Re-load from disk to verify persistence
        new_sm = SettingsManager(settings_file=self.settings_file)
        self.assertEqual(new_sm.get_client_agent_path(), str(self.client_agent_file))

        # 2. Test destination disks
        self.assertEqual(len(self.settings.get_copy_destinations()), 0)
        dest1 = str(self.temp_dir / "usb_drive_1")
        dest2 = str(self.temp_dir / "usb_drive_2")

        self.assertTrue(self.settings.add_copy_destination(dest1))
        self.assertFalse(self.settings.add_copy_destination(dest1))  # duplicate
        self.assertTrue(self.settings.add_copy_destination(dest2))
        self.assertEqual(len(self.settings.get_copy_destinations()), 2)

        self.assertTrue(self.settings.remove_copy_destination(dest1))
        self.assertEqual(self.settings.get_copy_destinations(), [dest2])

        self.settings.clear_copy_destinations()
        self.assertEqual(len(self.settings.get_copy_destinations()), 0)

    def test_library_manager_scanning_and_missing_models(self):
        scan = self.library.scan_library()
        items = scan["items"]
        stats = scan["stats"]

        # Should find 4 articles
        self.assertEqual(len(items), 4)
        # 1 has model, 3 are missing models
        self.assertEqual(stats["total_models"], 1)
        self.assertEqual(stats["missing_models"], 3)

        # Scoping tests
        # By article
        art_items = self.library.get_articles_by_scope("article", "Architecture/Houses/101. Modern Villa")
        self.assertEqual(len(art_items), 1)
        self.assertTrue(art_items[0]["has_model"])

        # By category
        arch_items = self.library.get_articles_by_scope("category", "Architecture")
        self.assertEqual(len(arch_items), 3)

        # By subcategory
        houses_items = self.library.get_articles_by_scope(
            "subcategory", {"category": "Architecture", "subcategory": "Houses"}
        )
        self.assertEqual(len(houses_items), 2)

        # Missing models by scope
        all_missing = self.library.get_missing_items("all")
        self.assertEqual(len(all_missing), 3)

        houses_missing = self.library.get_missing_items(
            "subcategory", {"category": "Architecture", "subcategory": "Houses"}
        )
        self.assertEqual(len(houses_missing), 1)
        self.assertEqual(houses_missing[0]["title"], "102. Wooden Cabin")

        # Test scan_library with missing_only=True
        missing_scan = self.library.scan_library(missing_only=True)
        self.assertEqual(len(missing_scan["items"]), 3)
        self.assertTrue(all(not it["has_model"] for it in missing_scan["items"]))

        # Test scan_library with category_filter="Architecture" and missing_only=True
        arch_missing_scan = self.library.scan_library(category_filter="Architecture", missing_only=True)
        self.assertEqual(len(arch_missing_scan["items"]), 2)
        self.assertEqual({it["title"] for it in arch_missing_scan["items"]}, {"102. Wooden Cabin", "103. Glass Skyscraper"})

        # Test batch_download_missing with custom targets list
        custom_targets = ["Architecture/Houses/102. Wooden Cabin"]
        custom_res = batch_download_missing(
            scope="custom",
            target=custom_targets,
            library_mgr=self.library,
            download_fn=lambda **kw: {"success": True, "model_file": "dummy.skp"},
        )
        self.assertEqual(custom_res["total"], 1)
        self.assertEqual(custom_res["succeeded"], 1)

    def test_clear_library_missing_vs_all(self):
        # Mode: 'missing' should only delete articles lacking a model
        deleted = self.library.clear_library(mode="missing")
        self.assertEqual(deleted, 3)

        remaining_scan = self.library.scan_library()
        self.assertEqual(len(remaining_scan["items"]), 1)
        self.assertEqual(remaining_scan["items"][0]["title"], "101. Modern Villa")

        # Mode: 'all' should delete everything
        deleted_all = self.library.clear_library(mode="all")
        self.assertEqual(deleted_all, 1)

        empty_scan = self.library.scan_library()
        self.assertEqual(len(empty_scan["items"]), 0)

    def test_copy_manager_multi_destination_with_client_agent(self):
        copy_mgr = CopyManager()

        # Destination disks (e.g. 2 USB drives)
        dest_disk1 = self.temp_dir / "target_disk_A"
        dest_disk2 = self.temp_dir / "target_disk_B"
        dest_disk1.mkdir(parents=True, exist_ok=True)
        dest_disk2.mkdir(parents=True, exist_ok=True)

        # Set client agent
        self.settings.set_client_agent_path(str(self.client_agent_file))

        # Copy by Subcategory: Architecture -> Houses (2 articles)
        result = copy_mgr.copy_articles(
            scope="subcategory",
            target={"category": "Architecture", "subcategory": "Houses"},
            destinations=[str(dest_disk1), str(dest_disk2)],
            include_client_agent=True,
            client_agent_path=str(self.client_agent_file),
            library_mgr=self.library,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["copied_articles"], 1)
        self.assertEqual(result["destinations_count"], 2)
        self.assertEqual(result["client_agent_copied"], 2)

        # Verify client agent was copied to root of both destination disks
        self.assertTrue((dest_disk1 / "client_agent.exe").exists())
        self.assertTrue((dest_disk2 / "client_agent.exe").exists())
        self.assertEqual((dest_disk1 / "client_agent.exe").read_bytes(), b"MZ_DUMMY_CLIENT_AGENT_BINARY_EXE")
        self.assertEqual((dest_disk2 / "client_agent.exe").read_bytes(), b"MZ_DUMMY_CLIENT_AGENT_BINARY_EXE")

        # Verify articles structure on both disks (in storage folder)
        # Note: only finished models are copied; incomplete articles without models are skipped.
        # Furthermore, .zip model archives are automatically unzipped and the .zip deleted.
        art1_on_disk1 = dest_disk1 / "storage" / "Architecture" / "Houses" / "101. Modern Villa"
        art2_on_disk1 = dest_disk1 / "storage" / "Architecture" / "Houses" / "102. Wooden Cabin"
        self.assertTrue((art1_on_disk1 / "model" / "villa.skp").exists())
        self.assertFalse((art1_on_disk1 / "model" / "villa.zip").exists())
        self.assertTrue((art1_on_disk1 / "image_1.jpg").exists())
        self.assertFalse(art2_on_disk1.exists())

        art1_on_disk2 = dest_disk2 / "storage" / "Architecture" / "Houses" / "101. Modern Villa"
        art2_on_disk2 = dest_disk2 / "storage" / "Architecture" / "Houses" / "102. Wooden Cabin"
        self.assertTrue((art1_on_disk2 / "model" / "villa.skp").exists())
        self.assertFalse((art1_on_disk2 / "model" / "villa.zip").exists())
        self.assertTrue((art1_on_disk2 / "image_1.jpg").exists())
        self.assertFalse(art2_on_disk2.exists())

    def test_copy_by_single_article(self):
        copy_mgr = CopyManager()
        dest_disk = self.temp_dir / "target_disk_single"
        dest_disk.mkdir(parents=True, exist_ok=True)

        result = copy_mgr.copy_articles(
            scope="article",
            target="Architecture/Houses/101. Modern Villa",
            destinations=[str(dest_disk)],
            include_client_agent=True,
            client_agent_path=str(self.client_agent_file),
            library_mgr=self.library,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["copied_articles"], 1)
        self.assertTrue((dest_disk / "client_agent.exe").exists())
        self.assertTrue((dest_disk / "storage" / "Architecture" / "Houses" / "101. Modern Villa" / "model" / "villa.skp").exists())
        self.assertFalse((dest_disk / "storage" / "Architecture" / "Houses" / "101. Modern Villa" / "model" / "villa.zip").exists())

    def test_batch_download_missing_by_scopes(self):
        # Mock download function
        def mock_downloader(article_url, download_model, download_imgs, target_article_dir, log_cb=None):
            m_dir = Path(target_article_dir) / "model"
            m_dir.mkdir(parents=True, exist_ok=True)
            zip_file = m_dir / "model.zip"
            zip_file.write_bytes(b"MOCK_ZIP_BYTES")
            return {"success": True, "model_file": str(zip_file)}

        # Pre-populate article_url in meta so we don't query network
        art2 = self.feeds_dir / "Architecture" / "Houses" / "102. Wooden Cabin"
        self.library.save_meta(art2, {"article_url": "https://sketchup.cgtips.org/cabin/"})

        # 1. Re-download by Subcategory (Houses) - 1 missing
        res_sub = batch_download_missing(
            scope="subcategory",
            target={"category": "Architecture", "subcategory": "Houses"},
            library_mgr=self.library,
            download_fn=mock_downloader,
        )
        self.assertEqual(res_sub["total"], 1)
        self.assertEqual(res_sub["succeeded"], 1)
        self.assertTrue((art2 / "model" / "model.zip").exists())

        # Now only 2 missing models left in library (103 and 104)
        art3 = self.feeds_dir / "Architecture" / "Towers" / "103. Glass Skyscraper"
        self.library.save_meta(art3, {"article_url": "https://sketchup.cgtips.org/skyscraper/"})

        art4 = self.feeds_dir / "Direct_Downloads" / "104. Leather Couch"
        self.library.save_meta(art4, {"article_url": "https://sketchup.cgtips.org/couch/"})

        # 2. Re-download all remaining missing models
        res_all = batch_download_missing(
            scope="all",
            library_mgr=self.library,
            download_fn=mock_downloader,
        )
        self.assertEqual(res_all["total"], 2)
        self.assertEqual(res_all["succeeded"], 2)
        self.assertTrue((art3 / "model" / "model.zip").exists())
        self.assertTrue((art4 / "model" / "model.zip").exists())

        # Now 0 missing models left
        self.assertEqual(len(self.library.get_missing_items("all")), 0)

    def test_batch_downloader_auto_retry(self):
        art = self.feeds_dir / "Architecture" / "Houses" / "102. Wooden Cabin"
        self.library.save_meta(art, {"article_url": "https://sketchup.cgtips.org/cabin/"})

        call_count = 0
        def fail_then_succeed_downloader(article_url, download_model, download_imgs, target_article_dir, log_cb=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt fails
                return {"success": False, "model_file": None}
            # Second attempt succeeds
            m_dir = Path(target_article_dir) / "model"
            m_dir.mkdir(parents=True, exist_ok=True)
            zip_file = m_dir / "cabin.zip"
            zip_file.write_bytes(b"RETRY_SUCCESS_BYTES")
            return {"success": True, "model_file": str(zip_file)}

        res = batch_download_missing(
            scope="subcategory",
            target={"category": "Architecture", "subcategory": "Houses"},
            library_mgr=self.library,
            download_fn=fail_then_succeed_downloader,
            is_auto_retry_active=lambda: True,
        )

        self.assertEqual(call_count, 2)
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["succeeded"], 1)
        self.assertEqual(res["failed"], 0)
        self.assertTrue((art / "model" / "cabin.zip").exists())

    def test_app_bridge_auto_retry_and_clipboard(self):
        from PySide6.QtWidgets import QApplication
        from desktop.backend.app_bridge import AppBridge

        # Ensure QApplication instance exists
        app = QApplication.instance() or QApplication([])

        bridge = AppBridge()
        self.assertFalse(bridge.autoRetryEnabled)

        # Toggle auto-retry
        bridge.toggleAutoRetry()
        self.assertTrue(bridge.autoRetryEnabled)

        bridge.toggleAutoRetry()
        self.assertFalse(bridge.autoRetryEnabled)

        bridge.setAutoRetryEnabled(True)
        self.assertTrue(bridge.autoRetryEnabled)

        # Clipboard copy
        bridge.copyToClipboard("Test line 1\nTest line 2")
        from PySide6.QtGui import QGuiApplication
        clip = QGuiApplication.clipboard()
        if clip:
            self.assertEqual(clip.text(), "Test line 1\nTest line 2")

    def test_settings_manager_api_config(self):
        # Default API URL
        self.assertEqual(self.settings.get_api_url(), "https://loftdesign.bilnov.com/api")
        self.assertEqual(self.settings.get_api_username(), "")
        self.assertEqual(self.settings.get_api_password(), "")

        # Set API credentials
        self.settings.set_api_url("https://custom.loftdesign.com")
        self.settings.set_api_username("admin_test")
        self.settings.set_api_password("secret_pass_123")

        # Test persistence
        loaded = SettingsManager(settings_file=self.settings_file)
        self.assertEqual(loaded.get_api_url(), "https://custom.loftdesign.com")
        self.assertEqual(loaded.get_api_username(), "admin_test")
        self.assertEqual(loaded.get_api_password(), "secret_pass_123")

        # Config dict
        cfg = loaded.get_api_config()
        self.assertEqual(cfg["api_url"], "https://custom.loftdesign.com")
        self.assertEqual(cfg["username"], "admin_test")
        self.assertEqual(cfg["password"], "secret_pass_123")

    def test_upload_manager_test_connection(self):
        up_mgr = UploadManager(library_mgr=self.library)

        # Missing credentials returns failure
        ok, msg = up_mgr.test_connection(api_url="https://loftdesign.bilnov.com", username="", password="")
        self.assertFalse(ok)
        self.assertIn("Username and password are required", msg)

        # Mocked successful 200 response
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp

            ok, msg = up_mgr.test_connection(
                api_url="https://loftdesign.bilnov.com",
                username="admin",
                password="password123",
            )
            self.assertTrue(ok)
            self.assertIn("Successfully connected", msg)
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            self.assertEqual(args[0], "https://loftdesign.bilnov.com/api/gallery/items")
            self.assertEqual(kwargs["auth"], ("admin", "password123"))

        # Mocked 401 unauthorized response
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.json.return_value = {"detail": "Invalid credentials"}
            mock_get.return_value = mock_resp

            ok, msg = up_mgr.test_connection(
                api_url="https://loftdesign.bilnov.com",
                username="wrong_user",
                password="wrong_password",
            )
            self.assertFalse(ok)
            self.assertIn("Authentication failed", msg)
            self.assertIn("Invalid credentials", msg)

    def test_upload_manager_upload_articles(self):
        up_mgr = UploadManager(library_mgr=self.library)

        # Missing credentials returns error
        res_empty = up_mgr.upload_articles(
            scope="all",
            api_url="https://loftdesign.bilnov.com",
            username="",
            password="",
            library_mgr=self.library,
        )
        self.assertEqual(res_empty.get("error"), "Missing credentials")

        # Mocked upload with 201 response for all scopes
        uploaded_payloads = []
        with patch("requests.post") as mock_post:
            def fake_post(url, files=None, data=None, auth=None, timeout=None):
                mock_r = MagicMock()
                mock_r.status_code = 201
                uploaded_payloads.append(dict(data))
                return mock_r

            mock_post.side_effect = fake_post

            # 1. Scope: article
            res_art = up_mgr.upload_articles(
                scope="article",
                target="Architecture/Houses/101. Modern Villa",
                api_url="https://loftdesign.bilnov.com",
                username="admin",
                password="password",
                library_mgr=self.library,
            )
            self.assertEqual(res_art["total"], 1)
            self.assertEqual(res_art["succeeded"], 1)
            self.assertEqual(res_art["failed"], 0)
            self.assertEqual(len(uploaded_payloads), 1)
            self.assertEqual(uploaded_payloads[0]["space_name"], "Architecture")
            self.assertEqual(uploaded_payloads[0]["category_name"], "Houses")
            self.assertEqual(uploaded_payloads[0]["reference"], "101. Modern Villa")
            self.assertEqual(uploaded_payloads[0]["is_default"], "true")

            # 2. Scope: subcategory
            uploaded_payloads.clear()
            res_sub = up_mgr.upload_articles(
                scope="subcategory",
                target={"category": "Architecture", "subcategory": "Houses"},
                api_url="https://loftdesign.bilnov.com",
                username="admin",
                password="password",
                library_mgr=self.library,
            )
            self.assertEqual(res_sub["total"], 2)
            self.assertEqual(res_sub["succeeded"], 2)
            self.assertEqual(len(uploaded_payloads), 2)

            # 3. Scope: category
            uploaded_payloads.clear()
            res_cat = up_mgr.upload_articles(
                scope="category",
                target="Architecture",
                api_url="https://loftdesign.bilnov.com",
                username="admin",
                password="password",
                library_mgr=self.library,
            )
            self.assertEqual(res_cat["total"], 3)
            self.assertEqual(res_cat["succeeded"], 3)
            self.assertEqual(len(uploaded_payloads), 3)

        # 4. Duplicate handling (HTTP 400 "already exists" is gracefully treated as succeeded)
        with patch("requests.post") as mock_post:
            mock_r = MagicMock()
            mock_r.status_code = 400
            mock_r.text = "Item with identical image already exists"
            mock_post.return_value = mock_r

            res_dup = up_mgr.upload_articles(
                scope="article",
                target="Architecture/Houses/101. Modern Villa",
                api_url="https://loftdesign.bilnov.com",
                username="admin",
                password="password",
                library_mgr=self.library,
            )
            self.assertEqual(res_dup["succeeded"], 1)

    def test_app_bridge_upload_methods(self):
        from PySide6.QtWidgets import QApplication
        from desktop.backend.app_bridge import AppBridge

        app = QApplication.instance() or QApplication([])
        bridge = AppBridge()

        # Test setApiConfig and getApiConfig
        bridge.setApiConfig("https://api.loftdesign.com", "user_bridge", "pass_bridge")
        cfg = bridge.getApiConfig()
        self.assertEqual(cfg["api_url"], "https://api.loftdesign.com")
        self.assertEqual(cfg["username"], "user_bridge")
        self.assertEqual(cfg["password"], "pass_bridge")

        # Test setApiCredentials
        bridge.setApiCredentials("admin_only", "pass_only")
        self.assertEqual(bridge.apiUsername, "admin_only")
        self.assertEqual(bridge.apiPassword, "pass_only")

        # Test getUploadArticlesForScope
        items = bridge.getUploadArticlesForScope("all")
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 0)


if __name__ == "__main__":
    unittest.main()


