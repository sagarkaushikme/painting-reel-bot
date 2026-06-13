"""
Painting Explained — Content Source.

Fetches random paintings from Rijksmuseum (Linked Data API) and Met Museum.
This is the museum-specific API logic extracted from the original downloader.
"""

import os
import json
import random
import logging
import requests
from pathlib import Path
from core.downloader import download_image

logger = logging.getLogger("content-automation")

# Paths — blacklist is now under config/blacklists/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLACKLIST_PATH = os.path.join(BASE_DIR, "config", "blacklists", "painting_explained.json")


# ============================================================
# BLACKLIST MANAGEMENT
# ============================================================


def _load_blacklist() -> dict:
    """Load the painting blacklist from disk."""
    try:
        with open(BLACKLIST_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_blacklist(blacklist: dict):
    """Save the painting blacklist to disk."""
    os.makedirs(os.path.dirname(BLACKLIST_PATH), exist_ok=True)
    with open(BLACKLIST_PATH, "w") as f:
        json.dump(blacklist, f, indent=2, ensure_ascii=False)


def is_already_posted(object_id: str) -> bool:
    """Check if a painting has already been posted."""
    blacklist = _load_blacklist()
    return str(object_id) in blacklist


def mark_as_posted(metadata: dict, page_id: str):
    """Add a painting to the blacklist after posting."""
    blacklist = _load_blacklist()
    object_id = metadata.get("object_id", "unknown")
    blacklist[str(object_id)] = {
        "title": metadata.get("title", "Unknown"),
        "artist": metadata.get("artist", "Unknown"),
        "posted_at": __import__("datetime").datetime.now().isoformat(),
    }
    _save_blacklist(blacklist)
    logger.info(f"📝 Blacklisted: {object_id} — {metadata.get('title', 'Unknown')}")


# ============================================================
# MAIN ENTRY POINT
# ============================================================


def get_content(config: dict, max_retries: int = 5) -> tuple:
    """
    Get a random famous painting from either source.
    50% chance Rijksmuseum, 50% chance Met Museum.
    Retries on failure, with fallback to other source.

    Returns: (image_path: str, metadata: dict)
    metadata = {title, artist, year, source, object_id, image_url}

    Raises: RuntimeError if all retries exhausted.
    """
    for attempt in range(1, max_retries + 1):
        logger.info(f"🎲 Attempt {attempt}/{max_retries} — fetching painting...")

        # For now, only Chicago Art Institute is implemented
        sources = [_fetch_from_artic]

        for source_fn in sources:
            source_name = "Chicago Art Institute"
            logger.info(f"🔍 Trying {source_name}...")

            image_path, metadata = source_fn()
            if image_path and metadata:
                logger.info(
                    f"✅ Got painting from {source_name}: "
                    f"{metadata['title']} by {metadata['artist']}"
                )
                return image_path, metadata

    raise RuntimeError(
        f"Failed to fetch painting after {max_retries} retries from both sources"
    )


# ============================================================
# SOURCE: CHICAGO ART INSTITUTE API
# ============================================================

def _fetch_from_artic() -> tuple:
    """
    Fetch a random famous painting from the Art Institute of Chicago.
    Returns: (image_path, metadata) or (None, None) on failure.
    """
    try:
        # We query for 'painting' and randomize the page to get different results
        page = random.randint(1, 100)
        search_url = "https://api.artic.edu/api/v1/artworks/search"
        params = {
            "q": "painting",
            "limit": 10,
            "page": page,
            "fields": "id,title,artist_display,date_display,image_id"
        }

        resp = requests.get(search_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", [])
        if not items:
            logger.warning("Chicago Art Institute: No items found")
            return None, None

        random.shuffle(items)

        for item in items:
            image_id = item.get("image_id")
            if not image_id:
                continue

            object_id = f"artic_{item.get('id')}"
            if is_already_posted(object_id):
                logger.info(f"⏭️ Skipping already posted: {object_id}")
                continue

            # Construct IIIF image URL
            # 843, is the default max width allowed for free downloads without a token
            image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
            image_path = f"/tmp/painting_{object_id}.jpg"

            if download_image(image_url, image_path):
                metadata = {
                    "object_id": object_id,
                    "title": item.get("title", "Unknown"),
                    "artist": item.get("artist_display", "Unknown").split("\\n")[0].strip(),
                    "year": item.get("date_display", "Unknown"),
                    "source": "chicago_art_institute"
                }
                return image_path, metadata

        logger.warning("Chicago Art Institute: Could not find suitable painting with image")
        return None, None

    except Exception as e:
        logger.error(f"Chicago Art Institute fetch error: {e}")
        return None, None
