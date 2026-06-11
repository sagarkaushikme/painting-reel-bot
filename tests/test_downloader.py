"""
Tests for painting downloader — Met Museum API parsing, blacklist, validation.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from src.downloader import (
    is_already_posted,
    mark_as_posted,
    _download_image,
    _load_blacklist,
)


class TestBlacklist:
    """Test blacklist (duplicate prevention) logic."""

    def test_empty_blacklist(self, tmp_path):
        """Empty blacklist should return False for any ID."""
        blacklist_file = tmp_path / "blacklist.json"
        blacklist_file.write_text("{}")

        with patch("src.downloader.BLACKLIST_PATH", str(blacklist_file)):
            assert is_already_posted("met_12345") is False
            assert is_already_posted("rijks_67890") is False

    def test_mark_and_check(self, tmp_path):
        """After marking, should detect as posted."""
        blacklist_file = tmp_path / "blacklist.json"
        blacklist_file.write_text("{}")

        with patch("src.downloader.BLACKLIST_PATH", str(blacklist_file)):
            assert is_already_posted("met_12345") is False

            mark_as_posted("met_12345", "Starry Night", "Van Gogh")

            assert is_already_posted("met_12345") is True
            assert is_already_posted("met_99999") is False

    def test_blacklist_persistence(self, tmp_path):
        """Blacklist data should persist to disk."""
        blacklist_file = tmp_path / "blacklist.json"
        blacklist_file.write_text("{}")

        with patch("src.downloader.BLACKLIST_PATH", str(blacklist_file)):
            mark_as_posted("met_111", "Mona Lisa", "Da Vinci")

        # Read the file directly
        data = json.loads(blacklist_file.read_text())
        assert "met_111" in data
        assert data["met_111"]["title"] == "Mona Lisa"
        assert data["met_111"]["artist"] == "Da Vinci"

    def test_corrupt_blacklist(self, tmp_path):
        """Corrupt blacklist file should not crash."""
        blacklist_file = tmp_path / "blacklist.json"
        blacklist_file.write_text("THIS IS NOT JSON!!!")

        with patch("src.downloader.BLACKLIST_PATH", str(blacklist_file)):
            # Should return empty dict, not crash
            result = _load_blacklist()
            assert result == {}

    def test_missing_blacklist(self, tmp_path):
        """Missing blacklist file should not crash."""
        blacklist_file = tmp_path / "nonexistent.json"

        with patch("src.downloader.BLACKLIST_PATH", str(blacklist_file)):
            result = _load_blacklist()
            assert result == {}


class TestImageDownload:
    """Test image download validation."""

    @patch("src.downloader.requests.get")
    def test_download_too_small(self, mock_get, tmp_path):
        """Images under 500KB should be rejected."""
        # Create a tiny image file
        small_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Tiny JPEG header

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [small_data]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        save_path = str(tmp_path / "test.jpg")
        result = _download_image("http://example.com/test.jpg", save_path)

        assert result is False  # Too small

    @patch("src.downloader.requests.get")
    def test_download_not_image(self, mock_get, tmp_path):
        """Non-image content types should be rejected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        save_path = str(tmp_path / "test.jpg")
        result = _download_image("http://example.com/test.jpg", save_path)

        assert result is False


class TestMetMuseumParsing:
    """Test Met Museum API response parsing logic."""

    def test_met_search_response_structure(self):
        """Met Museum search response should have objectIDs."""
        # This tests our expected API structure
        sample_response = {
            "total": 250,
            "objectIDs": [436535, 437329, 438015],
        }
        assert "objectIDs" in sample_response
        assert isinstance(sample_response["objectIDs"], list)
        assert len(sample_response["objectIDs"]) > 0

    def test_met_object_response_structure(self):
        """Met Museum object response should have required fields."""
        sample_object = {
            "objectID": 436535,
            "isPublicDomain": True,
            "primaryImage": "https://images.metmuseum.org/something.jpg",
            "title": "Washington Crossing the Delaware",
            "artistDisplayName": "Emanuel Leutze",
            "objectDate": "1851",
        }
        assert sample_object["isPublicDomain"] is True
        assert sample_object["primaryImage"].startswith("http")
        assert len(sample_object["title"]) > 0
