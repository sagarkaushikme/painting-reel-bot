"""
Generic Gemini Analyzer — Content analysis with structured output.

Uses the google-genai SDK. Model: gemini-2.5-flash.
The prompt comes from each page's prompts.py module.
"""

import os
import re
import json
import logging
import typing_extensions
from PIL import Image

logger = logging.getLogger("content-automation")


# ============================================================
# SCHEMAS FOR STRUCTURED OUTPUT
# ============================================================

class ZoomPoint(typing_extensions.TypedDict):
    zoom_level: float
    position: list[float]
    duration: float
    text: str
    text_position: str

class ReelSchema(typing_extensions.TypedDict):
    drama_score: int
    hidden_story: str
    mood: str
    music_intensity: str
    zoom_sequence: list[ZoomPoint]


# ============================================================
# GEMINI RESPONSE PARSING
# ============================================================


def parse_gemini_response(raw_text: str) -> dict:
    """
    Parse Gemini's response text into a valid zoom data dict.
    Handles markdown backticks, extra text, malformed JSON.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    # Remove markdown code block markers
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Try direct JSON parse
    try:
        data = json.loads(text)
        if _validate_zoom_data(data):
            return data
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object with regex
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if _validate_zoom_data(data):
                return data
        except json.JSONDecodeError:
            pass

    # Try fixing common issues: trailing commas
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        data = json.loads(cleaned)
        if _validate_zoom_data(data):
            return data
    except json.JSONDecodeError:
        pass

    logger.warning("⚠️ Could not parse Gemini response as valid JSON")
    return None


def _validate_zoom_data(data: dict) -> bool:
    """Validate the structure of zoom data."""
    if not isinstance(data, dict):
        return False

    if "zoom_sequence" not in data:
        return False

    sequence = data["zoom_sequence"]
    if not isinstance(sequence, list) or len(sequence) < 2:
        return False

    for point in sequence:
        required_keys = ["x_percent", "y_percent", "zoom_level", "duration_sec"]
        if not all(key in point for key in required_keys):
            return False

        # Validate ranges
        if not (0.0 <= point["x_percent"] <= 1.0):
            return False
        if not (0.0 <= point["y_percent"] <= 1.0):
            return False
        if not (0.5 <= point["zoom_level"] <= 10.0):
            return False
        if not (1 <= point["duration_sec"] <= 15):
            return False

    return True


def _default_zoom_sequence(title: str, artist: str) -> dict:
    """
    Fallback zoom sequence when Gemini fails or returns invalid data.
    Simple center-zoom with generic text.
    """
    return {
        "drama_score": 5,
        "mood": "mysterious",
        "music_intensity": "medium",
        "hidden_story": f"A masterpiece by {artist} that changed art forever",
        "zoom_sequence": [
            {
                "order": 1,
                "what_is_here": "full painting — establish the scene",
                "x_percent": 0.5,
                "y_percent": 0.5,
                "zoom_level": 1.0,
                "duration_sec": 3,
                "text": "Iss painting ka sabse bada raaz...",
                "text_position": "bottom",
            },
            {
                "order": 2,
                "what_is_here": "center detail — most prominent element",
                "x_percent": 0.5,
                "y_percent": 0.3,
                "zoom_level": 2.5,
                "duration_sec": 5,
                "text": "Kya tumne notice kiya?",
                "text_position": "bottom",
            },
            {
                "order": 3,
                "what_is_here": "another detail",
                "x_percent": 0.4,
                "y_percent": 0.4,
                "zoom_level": 3.0,
                "duration_sec": 5,
                "text": "Kyunki sach kuch aur hi hai...",
                "text_position": "top",
            },
            {
                "order": 4,
                "what_is_here": "final detail twist",
                "x_percent": 0.6,
                "y_percent": 0.6,
                "zoom_level": 3.5,
                "duration_sec": 4,
                "text": "Hosh ud jayenge!",
                "text_position": "bottom",
            },
            {
                "order": 5,
                "what_is_here": "full painting reveal",
                "x_percent": 0.5,
                "y_percent": 0.5,
                "zoom_level": 1.0,
                "duration_sec": 3,
                "text": "",
                "text_position": "bottom",
            },
        ],
    }


# ============================================================
# MAIN ANALYSIS FUNCTION — GENERIC
# ============================================================


def analyze_content(image_path: str, vision_prompt: str, metadata: dict) -> dict:
    """
    Generic content analysis via Gemini 2.5 Flash Vision.

    Args:
        image_path: Path to image (can be None for text-only content like paisa_ka_gyaan)
        vision_prompt: The prompt template from the page's prompts.py
        metadata: Content metadata dict for prompt formatting

    Returns: zoom data dict with coordinates, text, drama score, etc.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not set")
        return _default_zoom_sequence(
            metadata.get("title", "Unknown"),
            metadata.get("artist", "Unknown"),
        )

    # Format the prompt with metadata fields
    try:
        prompt = vision_prompt.format(**metadata)
    except KeyError as e:
        logger.warning(f"⚠️ Prompt formatting error: {e}, using raw prompt")
        prompt = vision_prompt

    try:
        # Use new google-genai SDK
        from google import genai

        client = genai.Client(api_key=api_key)

        logger.info(f"🤖 Sending to Gemini 2.5 Flash...")

        # Build contents list — include image only if provided
        contents = []
        if image_path:
            image = Image.open(image_path)
            contents.append(image)
        contents.append(prompt)

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=contents,
        )

        # Extract text from response — handle thinking model responses
        raw_text = None
        try:
            raw_text = response.text
        except Exception:
            pass

        if raw_text is None:
            # Try extracting from candidates directly
            try:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        # Skip thinking/thought parts
                        if hasattr(part, "thought") and part.thought:
                            continue
                        if hasattr(part, "text") and part.text:
                            raw_text = part.text
                            break
                    if raw_text:
                        break
            except Exception as e:
                logger.warning(f"⚠️ Could not extract text from response: {e}")

        if not raw_text:
            logger.warning("⚠️ Gemini returned empty response")
            return _default_zoom_sequence(
                metadata.get("title", "Unknown"),
                metadata.get("artist", "Unknown"),
            )

        logger.info(f"🤖 Gemini responded ({len(raw_text)} chars)")

        # Parse the response
        zoom_data = parse_gemini_response(raw_text)

        if zoom_data is None:
            logger.warning("⚠️ Gemini response invalid, using default sequence")
            return _default_zoom_sequence(
                metadata.get("title", "Unknown"),
                metadata.get("artist", "Unknown"),
            )

        # Ensure text field exists for all points
        for point in zoom_data.get("zoom_sequence", []):
            if "text" not in point:
                point["text"] = metadata.get("title", "")
            if "text_position" not in point:
                point["text_position"] = "bottom"

        drama_score = zoom_data.get("drama_score", 5)
        logger.info(
            f"🎯 Analysis complete — Drama: {drama_score}/10, "
            f"Scenes: {len(zoom_data.get('zoom_sequence', []))}"
        )

        return zoom_data

    except ImportError:
        logger.error(
            "❌ google-genai not installed. Run: pip install google-genai"
        )
        return _default_zoom_sequence(
            metadata.get("title", "Unknown"),
            metadata.get("artist", "Unknown"),
        )

    except Exception as e:
        logger.error(f"❌ Gemini API error: {e}")
        return _default_zoom_sequence(
            metadata.get("title", "Unknown"),
            metadata.get("artist", "Unknown"),
        )
