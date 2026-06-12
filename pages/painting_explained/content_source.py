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

        # Alternate between sources, with randomness
        if random.random() < 0.5:
            sources = [_fetch_from_met_museum, _fetch_from_rijksmuseum]
        else:
            sources = [_fetch_from_rijksmuseum, _fetch_from_met_museum]

        for source_fn in sources:
            source_name = (
                "Met Museum"
                if "met" in source_fn.__name__
                else "Rijksmuseum"
            )
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
# SOURCE A: RIJKSMUSEUM (New Linked Data API)
# ============================================================


def _fetch_from_rijksmuseum() -> tuple:
    """
    Fetch a random painting from Rijksmuseum.
    Returns: (image_path, metadata) or (None, None) on failure.
    """
    try:
        # Step 1: Search for paintings with images
        search_url = "https://data.rijksmuseum.nl/search/collection"
        params = {
            "type": "painting",
            "imageAvailable": "true",
            "material": "canvas",  # Oil on canvas — more likely to be famous
        }

        # Randomly paginate to get different paintings each time
        resp = requests.get(search_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Get items from current page
        items = data.get("orderedItems", [])
        if not items:
            logger.warning("Rijksmuseum: No items in search results")
            return None, None

        # If there's a next page, randomly decide to go deeper (up to 5 pages)
        current_data = data
        max_pages = random.randint(1, 5)
        for _ in range(max_pages):
            next_page = current_data.get("next", {})
            next_url = next_page.get("id") if isinstance(next_page, dict) else None
            if not next_url:
                break
            try:
                resp = requests.get(next_url, timeout=30)
                resp.raise_for_status()
                current_data = resp.json()
                new_items = current_data.get("orderedItems", [])
                if new_items:
                    items = new_items  # Use the later page's items
            except Exception:
                break

        # Step 2: Pick a random item and resolve its LOD identifier
        random.shuffle(items)

        for item in items[:10]:  # Try up to 10 items
            lod_id = item.get("id", "")
            if not lod_id:
                continue

            # Extract numeric ID for blacklist tracking
            object_id = f"rijks_{lod_id.split('/')[-1]}"
            if is_already_posted(object_id):
                logger.info(f"⏭️ Skipping already posted: {object_id}")
                continue

            # Resolve the LOD identifier to get metadata
            metadata = _resolve_rijksmuseum_id(lod_id)
            if not metadata:
                continue

            # Step 3: Download the image
            image_url = metadata.get("image_url")
            if not image_url:
                continue

            image_path = f"/tmp/painting_{object_id}.jpg"
            if download_image(image_url, image_path):
                metadata["object_id"] = object_id
                metadata["source"] = "rijksmuseum"
                return image_path, metadata

        logger.warning("Rijksmuseum: Could not find suitable painting")
        return None, None

    except Exception as e:
        logger.error(f"Rijksmuseum fetch error: {e}")
        return None, None


def _resolve_rijksmuseum_id(lod_id: str) -> dict:
    """
    Resolve a Rijksmuseum LOD identifier to get metadata and image URL.
    Uses content negotiation to request JSON-LD.
    """
    try:
        # Request JSON-LD representation
        headers = {
            "Accept": "application/ld+json",
        }
        resp = requests.get(lod_id, headers=headers, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            # Try with query parameter approach
            if "?" in lod_id:
                resolve_url = f"{lod_id}&format=jsonld"
            else:
                resolve_url = f"{lod_id}?format=jsonld"
            resp = requests.get(resolve_url, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            return None

        data = resp.json()

        # Parse JSON-LD to extract metadata
        if isinstance(data, list):
            data = data[0] if data else {}

        # Extract title
        title = "Unknown"
        if "_label" in data:
            title = data["_label"]
        elif "label" in data:
            label = data["label"]
            if isinstance(label, dict):
                title = label.get("en", [label.get("nl", ["Unknown"])])[0]
                if isinstance(title, dict):
                    title = title.get("@value", "Unknown")
            elif isinstance(label, str):
                title = label

        # Extract artist/creator
        artist = "Unknown Artist"
        for key in ["produced_by", "created_by", "carried_out_by"]:
            if key in data:
                prod = data[key]
                if isinstance(prod, dict):
                    carried = prod.get("carried_out_by", [])
                    if isinstance(carried, list) and carried:
                        actor = carried[0]
                        artist = actor.get("_label", artist)
                    elif isinstance(carried, dict):
                        artist = carried.get("_label", artist)

        # Extract year
        year = "Unknown"
        timespan = data.get("produced_by", {}).get("timespan", {})
        if isinstance(timespan, dict):
            begin = timespan.get("begin_of_the_begin", "")
            if begin:
                year = begin[:4]

        # Extract image URL — look for IIIF representation
        image_url = None

        for key in ["representation", "digitally_shown_by", "subject_of"]:
            representations = data.get(key, [])
            if isinstance(representations, dict):
                representations = [representations]
            if isinstance(representations, list):
                for rep in representations:
                    rep_id = rep.get("id", "")
                    if "iiif" in rep_id.lower() or "micr.io" in rep_id.lower():
                        image_url = _extract_iiif_image(rep_id)
                        if image_url:
                            break
                    elif rep_id.endswith((".jpg", ".jpeg", ".png")):
                        image_url = rep_id
                        break

        # Fallback: construct IIIF URL from the LOD ID
        if not image_url:
            numeric_id = lod_id.rstrip("/").split("/")[-1]
            iiif_attempts = [
                f"https://iiif.micr.io/{numeric_id}/full/max/0/default.jpg",
                f"https://lh3.googleusercontent.com/proxy/{numeric_id}",
            ]
            for attempt_url in iiif_attempts:
                try:
                    head_resp = requests.head(attempt_url, timeout=10)
                    if head_resp.status_code == 200:
                        image_url = attempt_url
                        break
                except Exception:
                    continue

        if not image_url:
            return None

        return {
            "title": title,
            "artist": artist,
            "year": year,
            "image_url": image_url,
        }

    except Exception as e:
        logger.debug(f"Rijksmuseum resolve error for {lod_id}: {e}")
        return None


def _extract_iiif_image(manifest_url: str) -> str:
    """
    Extract a downloadable image URL from a IIIF manifest.
    """
    try:
        resp = requests.get(manifest_url, timeout=15)
        if resp.status_code != 200:
            return None

        data = resp.json()

        # IIIF Presentation API v3
        canvases = data.get("items", [])
        if not canvases and "sequences" in data:
            # IIIF v2
            sequences = data.get("sequences", [])
            if sequences:
                canvases = sequences[0].get("canvases", [])

        for canvas in canvases:
            items = canvas.get("items", canvas.get("images", []))
            if isinstance(items, list):
                for item in items:
                    body = item.get("body", item.get("resource", {}))
                    if isinstance(body, dict):
                        img_id = body.get("id", body.get("@id", ""))
                        if img_id:
                            if "/info.json" in img_id:
                                return img_id.replace(
                                    "/info.json", "/full/max/0/default.jpg"
                                )
                            return img_id
                    # Nested annotation pages (IIIF v3)
                    sub_items = item.get("items", [])
                    for sub in sub_items:
                        body = sub.get("body", {})
                        if isinstance(body, dict):
                            img_id = body.get("id", "")
                            if img_id:
                                return img_id

        return None
    except Exception:
        return None
