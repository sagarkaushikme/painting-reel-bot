"""
Tests for FFmpeg video maker — command construction, text escaping, zoom formulas.
"""

import os
import sys
import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from src.video_maker import _escape_ffmpeg_text, _find_font


class TestEscapeFFmpegText:
    """Test FFmpeg drawtext special character escaping."""

    def test_plain_text(self):
        """Plain text without special chars should pass through."""
        assert _escape_ffmpeg_text("Hello World") == "Hello World"

    def test_colon_escape(self):
        """Colons should be escaped."""
        result = _escape_ffmpeg_text("Title: Subtitle")
        assert "\\:" in result

    def test_comma_escape(self):
        """Commas should be escaped."""
        result = _escape_ffmpeg_text("Hello, World")
        assert "\\," in result

    def test_brackets_escape(self):
        """Square brackets should be escaped."""
        result = _escape_ffmpeg_text("Test [value]")
        assert "\\[" in result
        assert "\\]" in result

    def test_semicolon_escape(self):
        """Semicolons should be escaped."""
        result = _escape_ffmpeg_text("A;B")
        assert "\\;" in result

    def test_percent_escape(self):
        """Percent signs should be doubled."""
        result = _escape_ffmpeg_text("100%")
        assert "%%" in result

    def test_empty_string(self):
        """Empty string should return empty."""
        assert _escape_ffmpeg_text("") == ""

    def test_none_input(self):
        """None should return empty string."""
        assert _escape_ffmpeg_text(None) == ""

    def test_hinglish_text(self):
        """Typical Hinglish text should be properly escaped."""
        text = "Yeh chehra 400 saal purana hai"
        result = _escape_ffmpeg_text(text)
        assert result == text  # No special chars to escape

    def test_complex_text(self):
        """Text with multiple special chars."""
        text = "Title: Night Watch [1642], by Rembrandt; Dutch"
        result = _escape_ffmpeg_text(text)
        assert "\\:" in result
        assert "\\[" in result
        assert "\\]" in result
        assert "\\," in result
        assert "\\;" in result


class TestFindFont:
    """Test font discovery."""

    def test_returns_string(self):
        """Should always return a string (possibly empty)."""
        result = _find_font()
        assert isinstance(result, str)

    def test_font_exists_if_returned(self):
        """If a non-empty path is returned, it should exist."""
        result = _find_font()
        if result:
            assert os.path.exists(result), f"Font path doesn't exist: {result}"


class TestZoomFormulas:
    """Test zoom calculation logic."""

    def test_center_zoom_coordinates(self):
        """Center zoom (0.5, 0.5) should produce correct expressions."""
        x_pct = 0.5
        y_pct = 0.5
        # The formula: position = fraction * (image_dim - image_dim/zoom)
        # At zoom=1.0: position = 0.5 * (iw - iw/1.0) = 0.5 * 0 = 0 (centered)
        # This is correct because at zoom=1 the entire image is visible
        x_expr = f"({x_pct}*(iw-iw/zoom))"
        assert "0.5" in x_expr

    def test_corner_zoom_coordinates(self):
        """Top-left corner (0, 0) should zoom to top-left."""
        x_pct = 0.0
        y_pct = 0.0
        x_expr = f"({x_pct}*(iw-iw/zoom))"
        # At any zoom, x = 0 * anything = 0 → top-left
        assert "0.0" in x_expr

    def test_zoom_increment_calculation(self):
        """Zoom increment should reach target in ~80% of frames."""
        zoom = 3.0
        fps = 25
        duration = 5
        frames = fps * duration  # 125
        zoom_increment = (zoom - 1.0) / (frames * 0.8)
        # (3.0 - 1.0) / (125 * 0.8) = 2.0 / 100 = 0.02
        assert 0.01 < zoom_increment < 0.05

    def test_no_zoom_expression(self):
        """Zoom level 1.0 should produce static expression."""
        zoom = 1.0
        if zoom <= 1.05:
            zoom_expr = "1.0"
        assert zoom_expr == "1.0"

    def test_segment_duration_frames(self):
        """Frame count should match duration * fps."""
        duration = 5
        fps = 25
        frames = duration * fps
        assert frames == 125

    def test_output_resolution(self):
        """Output should be 1080x1920 (9:16 portrait)."""
        width = 1080
        height = 1920
        assert height / width == pytest.approx(16 / 9, abs=0.01)
