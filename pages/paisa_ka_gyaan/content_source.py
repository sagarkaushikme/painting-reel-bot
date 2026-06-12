"""
Paisa Ka Gyaan — Content Source.

Unlike painting_explained (which downloads images), this page
GENERATES content from scratch using Gemini text generation.
No image download — the "image" (diary page background) is
created in the video_maker step using a static template.
"""

import json
import os
import random
import logging

logger = logging.getLogger("content-automation")

TOPIC_CATEGORIES = [
    "currency_history",
    "business_origin_story",
    "financial_concept_explained",
    "inflation_comparison",
    "famous_money_mistake",
    "investment_math_visual",
]


def get_content(config: dict) -> tuple:
    """
    Generate a finance topic using Gemini.

    Returns: (None, metadata)
    Note: No image download here — content_source generates
    TEXT content. The "image" (diary page background) is
    created in video_maker step using a static template.
    """
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    category = random.choice(TOPIC_CATEGORIES)

    # Check blacklist to avoid repeating topics
    used_topics = load_blacklist("paisa_ka_gyaan")

    prompt = f"""
Generate ONE finance/money fact or story for an Instagram Reel
in the category: {category}

Requirements:
- Must be FACTUAL and EDUCATIONAL (no investment advice,
  no "buy this stock", no guaranteed returns)
- Topic must be DIFFERENT from these already used: {used_topics}
- Should be genuinely interesting/surprising

Return ONLY JSON:
{{
  "topic_id": "short_unique_slug",
  "category": "{category}",
  "title": "Short title for internal reference",
  "facts": ["fact 1", "fact 2", "fact 3"]
}}
"""

    logger.info(f"🤖 Generating finance topic (category: {category})...")

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[prompt],
    )

    # Extract text — handle thinking model
    raw = None
    try:
        raw = response.text
    except Exception:
        pass

    if raw is None:
        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "thought") and part.thought:
                        continue
                    if hasattr(part, "text") and part.text:
                        raw = part.text
                        break
                if raw:
                    break
        except Exception as e:
            logger.error(f"❌ Could not extract text from Gemini response: {e}")
            raise RuntimeError("Gemini returned empty response for finance topic")

    if not raw:
        raise RuntimeError("Gemini returned empty response for finance topic")

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].replace("json", "", 1)

    data = json.loads(raw.strip())

    metadata = {
        "topic_id": data["topic_id"],
        "title": data["title"],
        "category": data["category"],
        "facts": data["facts"],
    }

    logger.info(f"📖 Topic generated: {metadata['title']} ({metadata['category']})")

    return None, metadata


def load_blacklist(page_id: str) -> list:
    """Load list of already-used topic IDs."""
    path = f"config/blacklists/{page_id}.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [item["topic_id"] for item in data.get("posted", [])]
    except (json.JSONDecodeError, KeyError):
        return []


def mark_as_posted(metadata: dict, page_id: str):
    """Record posted topic to avoid repeats."""
    path = f"config/blacklists/{page_id}.json"
    data = {"posted": []}
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {"posted": []}

    data["posted"].append({
        "topic_id": metadata["topic_id"],
        "title": metadata["title"],
        "posted_at": __import__("datetime").datetime.now().isoformat(),
    })

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"📝 Blacklisted topic: {metadata['topic_id']} — {metadata['title']}")
