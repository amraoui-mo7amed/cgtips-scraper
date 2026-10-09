import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils import (
    detect_download_provider,
    download_from_sharepoint,
    _normalize_sharepoint_download_url,
    _extract_sharepoint_filename,
)


class TestSharePointFeatures(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_download_provider_sharepoint(self):
        url = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/ESdJ5QWj26lFusadxrxRzpwB-9YEciLfWyWhgeoZeD_Tng?e=tIRy3M"
        self.assertEqual(detect_download_provider(url), "SharePoint")
        self.assertEqual(detect_download_provider("https://custom.sharepoint.com/file/123"), "SharePoint")

    def test_normalize_sharepoint_download_url(self):
        u1 = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc"
        self.assertEqual(_normalize_sharepoint_download_url(u1), u1 + "?download=1")

        u2 = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc?e=123"
        self.assertEqual(_normalize_sharepoint_download_url(u2), u2 + "&download=1")

        u3 = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc?e=123&download=1"
        self.assertEqual(_normalize_sharepoint_download_url(u3), u3)

    def test_extract_sharepoint_filename(self):
        # RFC 5987 UTF-8 encoded
        cd1 = "attachment; filename*=utf-8''5583%2e%20Sketchup%20Kitchen%2e%20Model%2erar; filename=\"5583.rar\""
        self.assertEqual(_extract_sharepoint_filename(cd1, ""), "5583. Sketchup Kitchen. Model.rar")

        # Standard quoted filename
        cd2 = 'attachment; filename="modern_chair_interior.zip"'
        self.assertEqual(_extract_sharepoint_filename(cd2, ""), "modern_chair_interior.zip")

        # URL path fallback
        cd3 = ""
        url = "https://cgtips-my.sharepoint.com/personal/share/Documents/3D_House_Model.rar?ga=1"
        self.assertEqual(_extract_sharepoint_filename(cd3, url), "3D_House_Model.rar")

    @patch("utils._download_sharepoint_curl")
    @patch("utils._download_sharepoint_stream")
    @patch("utils._download_sharepoint_playwright")
    def test_download_from_sharepoint_playwright_primary(self, mock_pw, mock_stream, mock_curl):
        mock_pw.return_value = str(self.temp_dir / "from_pw.rar")
        url = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc?e=123"

        mock_page = MagicMock()
        res = download_from_sharepoint(mock_page, url, self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_pw.rar"))
        mock_pw.assert_called_once()
        mock_stream.assert_not_called()
        mock_curl.assert_not_called()

    @patch("utils._download_sharepoint_curl")
    @patch("utils._download_sharepoint_stream")
    @patch("utils._download_sharepoint_playwright")
    def test_download_from_sharepoint_stream_fallback(self, mock_pw, mock_stream, mock_curl):
        mock_pw.return_value = None
        mock_stream.return_value = str(self.temp_dir / "from_stream.rar")
        url = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc?e=123"

        mock_page = MagicMock()
        res = download_from_sharepoint(mock_page, url, self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_stream.rar"))
        mock_pw.assert_called_once()
        mock_stream.assert_called_once()
        mock_curl.assert_not_called()

    @patch("utils._download_sharepoint_curl")
    @patch("utils._download_sharepoint_stream")
    @patch("utils._download_sharepoint_playwright")
    def test_download_from_sharepoint_curl_fallback(self, mock_pw, mock_stream, mock_curl):
        mock_pw.return_value = None
        mock_stream.return_value = None
        mock_curl.return_value = str(self.temp_dir / "from_curl.rar")
        url = "https://cgtips-my.sharepoint.com/:u:/g/personal/share_cgtips_org/abc?e=123"

        mock_page = MagicMock()
        res = download_from_sharepoint(mock_page, url, self.temp_dir)
        self.assertEqual(res, str(self.temp_dir / "from_curl.rar"))
        mock_pw.assert_called_once()
        mock_stream.assert_called_once()
        mock_curl.assert_called_once()


if __name__ == "__main__":
    unittest.main()
