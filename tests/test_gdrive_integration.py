import json
import shutil
import tempfile
import unittest
from pathlib import Path

import config
import gdrive_api
from desktop.backend.settings_manager import SettingsManager


class TestGDriveIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cgtips_test_gdrive_")
        self.old_data_dir = config.DATA_DIR
        self.old_credentials_file = config.CREDENTIALS_FILE
        self.old_token_file = config.TOKEN_FILE

        config.DATA_DIR = Path(self.temp_dir) / "data"
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.CREDENTIALS_FILE = config.DATA_DIR / "credentials.json"
        config.TOKEN_FILE = config.DATA_DIR / "token.pickle"

        self.settings_file = config.DATA_DIR / "settings.json"
        self.settings = SettingsManager(settings_file=self.settings_file)

    def tearDown(self):
        config.DATA_DIR = self.old_data_dir
        config.CREDENTIALS_FILE = self.old_credentials_file
        config.TOKEN_FILE = self.old_token_file
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_status_missing_credentials(self):
        status = gdrive_api.check_gdrive_status()
        self.assertFalse(status["credentials_present"])
        self.assertFalse(status["authenticated"])
        self.assertIn("credentials.json", status["details"])

    def test_import_invalid_credentials(self):
        # Invalid JSON
        res = gdrive_api.import_credentials_content("not-json")
        self.assertFalse(res["success"])

        # Valid JSON but missing installed/web
        res = gdrive_api.import_credentials_content('{"some": "data"}')
        self.assertFalse(res["success"])

        # Missing client_id
        res = gdrive_api.import_credentials_content('{"installed": {"project_id": "test"}}')
        self.assertFalse(res["success"])

    def test_import_valid_credentials(self):
        valid_json = {
            "installed": {
                "client_id": "test-client-id-123.apps.googleusercontent.com",
                "project_id": "test-cgtips-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_secret": "test-secret-456",
                "redirect_uris": ["http://localhost"]
            }
        }
        res = gdrive_api.import_credentials_content(json.dumps(valid_json))
        self.assertTrue(res["success"])
        self.assertEqual(res["client_id"], "test-client-id-123.apps.googleusercontent.com")
        self.assertEqual(res["project_id"], "test-cgtips-project")

        # Verify status updates
        status = gdrive_api.check_gdrive_status()
        self.assertTrue(status["credentials_present"])
        self.assertFalse(status["authenticated"])
        self.assertEqual(status["client_id"], "test-client-id-123.apps.googleusercontent.com")

    def test_import_credentials_file(self):
        test_file = Path(self.temp_dir) / "my_credentials.json"
        valid_json = {
            "installed": {
                "client_id": "file-client-id.apps.googleusercontent.com",
                "client_secret": "file-secret",
                "project_id": "file-project"
            }
        }
        test_file.write_text(json.dumps(valid_json), encoding="utf-8")

        res = gdrive_api.import_credentials_file(str(test_file))
        self.assertTrue(res["success"])
        self.assertEqual(res["client_id"], "file-client-id.apps.googleusercontent.com")

    def test_disconnect_and_settings(self):
        self.assertFalse(self.settings.get_prefer_gdrive_api())
        self.settings.set_prefer_gdrive_api(True)
        self.assertTrue(self.settings.get_prefer_gdrive_api())

        self.settings.set_gdrive_user_info("user@example.com", "Test User")
        info = self.settings.get_gdrive_user_info()
        self.assertEqual(info["email"], "user@example.com")
        self.assertEqual(info["name"], "Test User")

        # Disconnect
        disc = gdrive_api.disconnect_gdrive(delete_credentials=True)
        self.assertTrue(disc["success"])
        status = gdrive_api.check_gdrive_status()
        self.assertFalse(status["credentials_present"])


if __name__ == "__main__":
    unittest.main()
