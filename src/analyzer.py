"""
Gemini Vision Analyzer — Painting analysis with zoom coordinates + Hinglish text.

Uses the new google-genai SDK (replaces deprecated google-generativeai).
Model: gemini-2.5-flash (free tier: 250 requests/day)
"""

import os
import re
import json
import logging
import typing_extensions
from PIL import Image

logger = logging.getLogger("painting-reel-bot")

# ============================================================
# VISION PROMPT
# ============================================================

VISION_PROMPT = """You are a creative director making viral Instagram Reels about famous paintings.

Analyze this painting: "{title}" by {artist} ({year})

Your job: identify the most dramatic, shocking, or mysterious elements in this painting
and create a cinematic zoom sequence that will make viewers save and share this reel.

Follow this EXACT REEL PSYCHOLOGY for the 5 scenes:

Structure:
1. HOOK (Scene 1, 3 sec)
   - Shocking/relatable statement
   - Never title, always story
   - First 2 seconds mein brain ko "kya hua?" feel hona chahiye

2. SUSPENSE (Scene 2, 5 sec)  
   - Question raise karo
   - Jawab mat do abhi
   - Zoom karo us element pe jo mystery create kare

3. PARTIAL REVEAL (Scene 3, 5 sec)
   - Thoda batao — poora nahi
   - "Kyunki..." se shuru karo text
   - Viewer ko lagey "almost samjha"

4. TWIST/PUNCHLINE (Scene 4, 4 sec)
   - Asli shocking fact batao
   - Emotional ya funny hona chahiye
   - Tag-worthy moment

5. OUTRO (Scene 5, 3 sec)
   - Last frame pe koi text nahi — sirf painting
   - No text at all (empty string)

Return ONLY a valid JSON object with this exact structure:

{{
  "drama_score": <integer 1-10>,
  "hidden_story": "<one shocking/interesting fact about this painting, max 15 words>",
  "mood": "mysterious",
  "music_intensity": "medium",
  "zoom_sequence": [
    {{
      "order": 1,
      "what_is_here": "full painting — establish the scene",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.0,
      "duration_sec": 3,
      "text": "<HOOK text in Hinglish, max 7 words>",
      "text_position": "bottom"
    }},
    {{
      "order": 2,
      "what_is_here": "<describe exactly what is at this location in the painting>",
      "x_percent": <0.0 to 1.0, where 0=left, 1=right>,
      "y_percent": <0.0 to 1.0, where 0=top, 1=bottom>,
      "zoom_level": <2.0 to 4.0>,
      "duration_sec": 5,
      "text": "<SUSPENSE text in Hinglish, max 7 words>",
      "text_position": "bottom"
    }},
    {{
      "order": 3,
      "what_is_here": "<second most dramatic element location>",
      "x_percent": <0.0 to 1.0>,
      "y_percent": <0.0 to 1.0>,
      "zoom_level": <2.5 to 4.5>,
      "duration_sec": 5,
      "text": "<PARTIAL REVEAL text in Hinglish starting with 'Kyunki...', max 7 words>",
      "text_position": "top"
    }},
    {{
      "order": 4,
      "what_is_here": "<third dramatic element or detail>",
      "x_percent": <0.0 to 1.0>,
      "y_percent": <0.0 to 1.0>,
      "zoom_level": <2.0 to 4.0>,
      "duration_sec": 4,
      "text": "<TWIST/PUNCHLINE text in Hinglish, max 7 words>",
      "text_position": "bottom"
    }},
    {{
      "order": 5,
      "what_is_here": "full painting reveal",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.0,
      "duration_sec": 3,
      "text": "",
      "text_position": "bottom"
    }}
  ]
}}
```

CRITICAL RULES:
1. x_percent and y_percent are RELATIVE POSITIONS in the painting image (0.0 to 1.0).
2. zoom_level meaning: 1.0 = full painting, 2.0 = 50% zoom, 4.5 = extreme close-up.
3. Text style (Hinglish ONLY — Hindi + English mix is MANDATORY). All output text will be converted to lowercase in video.
4. NO painting title ever (except in the 'hidden_story' field if needed, but NEVER in the video 'text' field).
5. HOOK (Scene 1) RULES:
   - "OMG", "WOW", "Amazing" — kabhi nahi use karna.
   - Hook must start with the painting's HIDDEN STORY.
   - Example format: "[Time period] mein [shocking event] hua tha..." (e.g., "1889 mein ek pagalpan ka daura pada tha...")
6. TWIST (Scene 4) RULES:
   - Twist ek aisa fact hona chahiye jo viewer ko PATA NA HO (even for famous paintings).
   - Use your internal knowledge (Wikipedia-like backstory) to fetch this.
   - Agar backstory nahi mili → painting technique ya artist ki life ka shocking fact use karo.
7. ALWAYS end on an emotion — funny/sad/shocking.
8. Last frame (Scene 5) pe koi text nahi — sirf painting, strictly empty text ("").
9. Determine the painting's emotional mood. Choose exactly ONE from: dark_horror, mysterious, melancholic, epic, devotional, romantic.
10. Choose music_intensity:
    - high: if drama_score >= 8
    - medium: if drama_score 5-7  
    - low: if drama_score < 5
11. Return ONLY the JSON object. No explanation, no markdown backticks, no other text."""


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
# DEFAULT FALLBACK ZOOM SEQUENCE
# ============================================================


def _default_zoom_sequence(title: str, artist: str) -> dict:
    """
    Fallback zoom sequence when Gemini fails or returns invalid data.
    Simple center-zoom with painting title.
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


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================


def analyze_painting(image_path: str, metadata: dict) -> dict:
    """
    Send painting to Gemini 2.5 Flash Vision for analysis.
    Returns zoom data dict with coordinates, text, and drama score.

    Uses new google-genai SDK (non-deprecated).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not set")
        return _default_zoom_sequence(
            metadata.get("title", "Unknown"),
            metadata.get("artist", "Unknown"),
        )

    title = metadata.get("title", "Unknown")
    artist = metadata.get("artist", "Unknown Artist")
    year = metadata.get("year", "Unknown")

    # Format the prompt
    prompt = VISION_PROMPT.format(title=title, artist=artist, year=year)

    try:
        # Load image
        image = Image.open(image_path)

        # Use new google-genai SDK
        from google import genai

        client = genai.Client(api_key=api_key)

        logger.info(f"🤖 Sending to Gemini 2.5 Flash...")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, prompt],
        )

        # Extract text from response — handle thinking model responses
        # gemini-2.5-flash is a thinking model, so response.text may be None
        # Need to extract from candidates → parts, skipping "thought" parts
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
                        # Skip thinking/thought parts — we want the actual output
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
            return _default_zoom_sequence(title, artist)

        logger.info(f"🤖 Gemini responded ({len(raw_text)} chars)")

        # Parse the response
        zoom_data = parse_gemini_response(raw_text)

        if zoom_data is None:
            logger.warning("⚠️ Gemini response invalid, using default sequence")
            return _default_zoom_sequence(title, artist)

        # Drama score filter
        drama_score = zoom_data.get("drama_score", 5)
        if drama_score < 5:
            logger.info(
                f"⚠️ Drama score too low: {drama_score}/10 — "
                "this painting might be boring"
            )
            # Don't reject here — let the caller decide
            # But log the warning

        # Ensure text field exists for all points
        for point in zoom_data["zoom_sequence"]:
            if "text" not in point:
                point["text"] = title
            if "text_position" not in point:
                point["text_position"] = "bottom"

        logger.info(
            f"🎯 Analysis complete — Drama: {drama_score}/10, "
            f"Scenes: {len(zoom_data['zoom_sequence'])}"
        )

        return zoom_data

    except ImportError:
        logger.error(
            "❌ google-genai not installed. Run: pip install google-genai"
        )
        return _default_zoom_sequence(title, artist)

    except Exception as e:
        logger.error(f"❌ Gemini API error: {e}")
        return _default_zoom_sequence(title, artist)
