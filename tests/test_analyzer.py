"""
Tests for Gemini Vision analyzer — JSON parsing, fallbacks, validation.
"""

import os
import sys
import json
import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from src.analyzer import (
    parse_gemini_response,
    _validate_zoom_data,
    _default_zoom_sequence,
)


class TestParseGeminiResponse:
    """Test JSON parsing from Gemini's raw text output."""

    def test_clean_json(self):
        """Direct clean JSON should parse correctly."""
        raw = json.dumps(
            {
                "drama_score": 8,
                "hidden_story": "A hidden skull in the background",
                "zoom_sequence": [
                    {
                        "order": 1,
                        "x_percent": 0.5,
                        "y_percent": 0.5,
                        "zoom_level": 1.0,
                        "duration_sec": 3,
                        "text": "Dekho yeh painting",
                        "text_position": "bottom",
                    },
                    {
                        "order": 2,
                        "x_percent": 0.7,
                        "y_percent": 0.3,
                        "zoom_level": 3.0,
                        "duration_sec": 5,
                        "text": "Yeh chehra kaun hai?",
                        "text_position": "bottom",
                    },
                ],
            }
        )
        result = parse_gemini_response(raw)
        assert result is not None
        assert result["drama_score"] == 8
        assert len(result["zoom_sequence"]) == 2

    def test_json_with_markdown_backticks(self):
        """JSON wrapped in ```json ... ``` should be parsed."""
        raw = '```json\n{"drama_score": 7, "hidden_story": "test", "zoom_sequence": [{"order": 1, "x_percent": 0.5, "y_percent": 0.5, "zoom_level": 1.0, "duration_sec": 3, "text": "hello", "text_position": "bottom"}, {"order": 2, "x_percent": 0.3, "y_percent": 0.7, "zoom_level": 2.5, "duration_sec": 5, "text": "world", "text_position": "top"}]}\n```'
        result = parse_gemini_response(raw)
        assert result is not None
        assert result["drama_score"] == 7

    def test_json_with_extra_text(self):
        """JSON with surrounding explanation text should be extracted."""
        raw = 'Here is the analysis:\n\n{"drama_score": 9, "hidden_story": "test", "zoom_sequence": [{"order": 1, "x_percent": 0.5, "y_percent": 0.5, "zoom_level": 1.0, "duration_sec": 3, "text": "hi", "text_position": "bottom"}, {"order": 2, "x_percent": 0.2, "y_percent": 0.8, "zoom_level": 3.5, "duration_sec": 5, "text": "ho", "text_position": "top"}]}\n\nI hope this helps!'
        result = parse_gemini_response(raw)
        assert result is not None
        assert result["drama_score"] == 9

    def test_empty_response(self):
        """Empty response should return None."""
        assert parse_gemini_response("") is None
        assert parse_gemini_response(None) is None

    def test_completely_invalid(self):
        """Non-JSON garbage should return None."""
        assert parse_gemini_response("this is not json at all") is None

    def test_json_with_trailing_comma(self):
        """JSON with trailing commas should be handled."""
        raw = '{"drama_score": 6, "hidden_story": "test", "zoom_sequence": [{"order": 1, "x_percent": 0.5, "y_percent": 0.5, "zoom_level": 1.0, "duration_sec": 3, "text": "a", "text_position": "bottom",}, {"order": 2, "x_percent": 0.5, "y_percent": 0.5, "zoom_level": 2.0, "duration_sec": 4, "text": "b", "text_position": "top",},],}'
        result = parse_gemini_response(raw)
        assert result is not None


class TestValidateZoomData:
    """Test zoom data validation."""

    def test_valid_data(self):
        """Well-formed zoom data should pass."""
        data = {
            "drama_score": 8,
            "zoom_sequence": [
                {
                    "x_percent": 0.5,
                    "y_percent": 0.5,
                    "zoom_level": 1.0,
                    "duration_sec": 3,
                },
                {
                    "x_percent": 0.7,
                    "y_percent": 0.3,
                    "zoom_level": 3.0,
                    "duration_sec": 5,
                },
            ],
        }
        assert _validate_zoom_data(data) is True

    def test_missing_zoom_sequence(self):
        """Data without zoom_sequence should fail."""
        data = {"drama_score": 5}
        assert _validate_zoom_data(data) is False

    def test_empty_zoom_sequence(self):
        """Empty zoom sequence should fail."""
        data = {"zoom_sequence": []}
        assert _validate_zoom_data(data) is False

    def test_single_point(self):
        """Single zoom point should fail (need at least 2)."""
        data = {
            "zoom_sequence": [
                {
                    "x_percent": 0.5,
                    "y_percent": 0.5,
                    "zoom_level": 1.0,
                    "duration_sec": 3,
                }
            ]
        }
        assert _validate_zoom_data(data) is False

    def test_out_of_range_coordinates(self):
        """Coordinates outside 0-1 range should fail."""
        data = {
            "zoom_sequence": [
                {
                    "x_percent": 1.5,  # Out of range!
                    "y_percent": 0.5,
                    "zoom_level": 1.0,
                    "duration_sec": 3,
                },
                {
                    "x_percent": 0.5,
                    "y_percent": 0.5,
                    "zoom_level": 2.0,
                    "duration_sec": 5,
                },
            ],
        }
        assert _validate_zoom_data(data) is False

    def test_missing_required_keys(self):
        """Points missing required keys should fail."""
        data = {
            "zoom_sequence": [
                {"x_percent": 0.5, "y_percent": 0.5},  # Missing zoom_level, duration
                {"x_percent": 0.5, "y_percent": 0.5, "zoom_level": 2.0, "duration_sec": 5},
            ],
        }
        assert _validate_zoom_data(data) is False


class TestDefaultZoomSequence:
    """Test fallback zoom sequence."""

    def test_default_has_minimum_fields(self):
        """Default sequence should have all required fields."""
        result = _default_zoom_sequence("Night Watch", "Rembrandt")
        assert "drama_score" in result
        assert "hidden_story" in result
        assert "zoom_sequence" in result
        assert len(result["zoom_sequence"]) >= 2

    def test_default_starts_and_ends_at_zoom_1(self):
        """Default should start and end with zoom_level 1.0."""
        result = _default_zoom_sequence("Test", "Artist")
        sequence = result["zoom_sequence"]
        assert sequence[0]["zoom_level"] == 1.0
        assert sequence[-1]["zoom_level"] == 1.0

    def test_default_includes_artist(self):
        """Default hidden story should mention the artist."""
        result = _default_zoom_sequence("Test", "Vermeer")
        assert "Vermeer" in result["hidden_story"]
