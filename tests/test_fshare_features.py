import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from utils import detect_download_provider, download_from_fshare
from desktop.backend.app_bridge import _build_provider_index, _mark_downloaded
from desktop.backend.scraper_service import ScraperService


class TestFshareAndProviderFeatures(unittest.TestCase):

    def test_detect_download_provider(self):
        # Google Drive
        self.assertEqual(detect_download_provider("https://drive.google.com/file/d/12345/view"), "Google Drive")
        self.assertEqual(detect_download_provider("https://docs.google.com/uc?id=12345"), "Google Drive")

        # Fshare
        self.assertEqual(detect_download_provider("https://www.fshare.vn/file/SBV8987YYPB7"), "Fshare")
        self.assertEqual(detect_download_provider("https://fshare.vn/file/ABC123XYZ"), "Fshare")

        # MediaFire
        self.assertEqual(detect_download_provider("https://www.mediafire.com/file/xyz123/file.rar"), "MediaFire")

        # Mega
        self.assertEqual(detect_download_provider("https://mega.nz/file/xyz123#key"), "Mega")

        # Dropbox
        self.assertEqual(detect_download_provider("https://www.dropbox.com/s/xyz123/model.zip"), "Dropbox")

        # Unknown / None
        self.assertEqual(detect_download_provider("https://unknownhost.com/model.zip"), "Direct")
        self.assertEqual(detect_download_provider(""), "")
        self.assertEqual(detect_download_provider(None), "")

    def setUp(self):
        import tempfile
        import shutil
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("utils._download_fshare_guest")
    def test_download_from_fshare_guest_success(self, mock_guest):
        mock_guest.return_value = str(self.temp_dir / "model.rar")
        res = download_from_fshare("https://www.fshare.vn/file/SBV8987YYPB7", self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "model.rar"))
        mock_guest.assert_called_once()

    @patch("utils._download_fshare_ytdlp")
    @patch("utils._download_fshare_playwright")
    @patch("utils._download_fshare_guest")
    def test_download_from_fshare_fallback_to_playwright(self, mock_guest, mock_playwright, mock_ytdlp):
        # Guest fails
        mock_guest.return_value = None
        # Playwright succeeds
        mock_playwright.return_value = str(self.temp_dir / "from_pw.rar")

        mock_page = MagicMock()
        res = download_from_fshare(mock_page, "https://www.fshare.vn/file/SBV8987YYPB7", self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_pw.rar"))
        mock_guest.assert_called_once()
        mock_playwright.assert_called_once()
        mock_ytdlp.assert_not_called()

    @patch("utils._download_fshare_ytdlp")
    @patch("utils._download_fshare_playwright")
    @patch("utils._download_fshare_guest")
    def test_download_from_fshare_fallback_to_ytdlp(self, mock_guest, mock_playwright, mock_ytdlp):
        # Guest fails
        mock_guest.return_value = None
        # Playwright fails
        mock_playwright.return_value = None
        # yt-dlp succeeds
        mock_ytdlp.return_value = str(self.temp_dir / "from_ytdlp.rar")

        mock_page = MagicMock()
        res = download_from_fshare(mock_page, "https://www.fshare.vn/file/SBV8987YYPB7", self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_ytdlp.rar"))
        mock_guest.assert_called_once()
        mock_playwright.assert_called_once()
        mock_ytdlp.assert_called_once()

    @patch("utils._download_fshare_ytdlp")
    @patch("utils._download_fshare_guest")
    def test_download_from_fshare_headless_fallback_to_ytdlp(self, mock_guest, mock_ytdlp):
        # No browser page available: Guest fails -> directly tries yt-dlp
        mock_guest.return_value = None
        mock_ytdlp.return_value = str(self.temp_dir / "from_ytdlp.rar")

        res = download_from_fshare("https://www.fshare.vn/file/SBV8987YYPB7", self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_ytdlp.rar"))
        mock_guest.assert_called_once()
        mock_ytdlp.assert_called_once()

    def test_build_provider_index(self):
        items = [
            {"title": "Modern Chair", "article_url": "https://cgtips.org/chair", "provider": "Google Drive"},
            {"title": "Classic Desk", "article_url": "https://cgtips.org/desk", "provider": "Fshare"},
            {"title": "Simple Lamp", "article_url": "https://cgtips.org/lamp"},  # No provider
        ]
        index = _build_provider_index(items)
        self.assertEqual(index.get("https://cgtips.org/chair"), "Google Drive")
        self.assertEqual(index.get("https://cgtips.org/desk"), "Fshare")
        self.assertNotIn("https://cgtips.org/lamp", index)

    def test_mark_downloaded_with_provider(self):
        feed_items = [
            {"title": "Modern Chair", "link": "https://cgtips.org/chair/"},
            {"title": "Classic Desk", "link": "https://cgtips.org/desk/"},
        ]
        downloaded_index = {"https://cgtips.org/chair": "/path/chair"}
        provider_index = {
            "https://cgtips.org/chair": "Google Drive",
            "https://cgtips.org/desk": "Fshare",
        }

        marked = _mark_downloaded(feed_items, downloaded_index, provider_index)
        self.assertEqual(len(marked), 2)

        self.assertTrue(marked[0]["downloaded"])
        self.assertEqual(marked[0]["provider"], "Google Drive")
        self.assertEqual(marked[0]["local_folder"], "/path/chair")

        self.assertFalse(marked[1]["downloaded"])
        self.assertEqual(marked[1]["provider"], "Fshare")


if __name__ == "__main__":
    unittest.main()
