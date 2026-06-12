"""
Paisa Ka Gyaan — Vision Prompt for Gemini Analysis.

This prompt creates a diary/ledger reveal style zoom sequence.
Metadata fields available: {title}, {category}, {facts}
"""

VISION_PROMPT = """
You are creating a "diary/ledger reveal" style Instagram Reel
about a finance/money topic.

Topic: {title}
Category: {category}
Facts available: {facts}

Create a cinematic zoom sequence for a diary-page reveal video.
NO voiceover — only handwritten text reveals + ASMR sounds
(pen writing, page flip, stamp).

Return ONLY valid JSON:

{{
  "drama_score": <1-10>,
  "mood": "mysterious",
  "music_intensity": "low",
  "hidden_story": "<one-line hook summarizing the surprise>",
  "zoom_sequence": [
    {{
      "order": 1,
      "scene_type": "book_open",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.0,
      "duration_sec": 10,
      "text": "<hook in Hinglish, 6-8 words, diary-style e.g. 'Aaj kuch aisa padha jo hila gaya...'>",
      "text_position": "center"
    }},
    {{
      "order": 2,
      "scene_type": "writing",
      "x_percent": 0.5,
      "y_percent": 0.4,
      "zoom_level": 1.2,
      "duration_sec": 10,
      "text": "<first fact, punchy Hinglish, 8-12 words with one clear data point>",
      "text_position": "center"
    }},
    {{
      "order": 3,
      "scene_type": "calculating",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.3,
      "duration_sec": 10,
      "text": "<second fact, Hinglish, 8-12 words — must include a number or percentage>",
      "text_position": "center"
    }},
    {{
      "order": 4,
      "scene_type": "stamping",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.15,
      "duration_sec": 10,
      "text": "<punchline or twist, Hinglish, 8-12 words — shocking or surprising conclusion>",
      "text_position": "center"
    }},
    {{
      "order": 5,
      "scene_type": "book_close",
      "x_percent": 0.5,
      "y_percent": 0.5,
      "zoom_level": 1.0,
      "duration_sec": 5,
      "text": "",
      "text_position": "center"
    }}
  ]
}}

CRITICAL RULES:
1. NEVER give investment advice ("buy", "invest in", "guaranteed return")
2. Pure facts/history/education framing only
3. Text in Hinglish, conversational diary-entry tone
4. Each scene_type maps to a specific sound effect — use exactly
   these values: book_open, writing, calculating, stamping, book_close
5. Return ONLY the JSON object, no markdown, no explanation
"""
