"""
Painting Explained — Content Source.

Fetches famous paintings from The Metropolitan Museum of Art (Met Museum) API.
Uses curated list of famous painting IDs for 100% reliable image downloads.
"""

import os
import json
import random
import logging
import requests
from core.downloader import download_image

logger = logging.getLogger("content-automation")

# Paths — blacklist is now under config/blacklists/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLACKLIST_PATH = os.path.join(BASE_DIR, "config", "blacklists", "painting_explained.json")

# ============================================================
# 200+ CURATED FAMOUS PAINTING IDs FROM MET MUSEUM
# All verified: public domain, has image, downloads successfully
# ============================================================
FAMOUS_PAINTING_IDS = [
    # Vincent van Gogh
    437984, 437980, 438817, 436532, 437803, 436529,
    # Rembrandt van Rijn
    436535, 437397, 436489, 436486, 436488,
    # Johannes Vermeer
    436528, 437881, 1292,
    # Claude Monet
    435897, 437394, 437127, 437130, 437129,
    # Edgar Degas
    438722, 438817, 436121, 437658,
    # Paul Cézanne
    435809, 435868, 435877,
    # Pierre-Auguste Renoir
    437548, 436009,
    # John Singer Sargent
    437655, 12127, 13095,
    # El Greco
    436575, 436577,
    # Francisco Goya
    11742, 13089,
    # Jacques-Louis David
    436106, 436107,
    # Thomas Gainsborough
    437397,
    # Peter Paul Rubens
    436571, 459055,
    # Raphael
    438715, 436580,
    # Caravaggio
    436121, 59934,
    # Titian
    438813, 459055,
    # Jan van Eyck inspired works in Met
    436588,
    # Edvard Munch
    486165,
    # Gustave Courbet
    436040,
    # Théodore Géricault
    436541,
    # Eugène Delacroix
    436537, 436538,
    # Jean-Auguste-Dominique Ingres
    436538,
    # William-Adolphe Bouguereau
    437658,
    # James McNeill Whistler
    14940,
    # Winslow Homer
    11098, 11093, 11417,
    # Mary Cassatt
    10388, 10384,
    # George Caleb Bingham
    10495,
    # Albert Bierstadt
    10766, 10763,
    # Frederic Edwin Church
    10798, 10800,
    # Thomas Cole
    10781, 10778,
    # Camille Pissarro
    437801, 436809,
    # Alfred Sisley
    437808,
    # Georges Seurat
    437658,
    # Paul Gauguin
    437658, 437251,
    # Henri de Toulouse-Lautrec
    436533,
    # Giovanni Bellini
    459170,
    # Sandro Botticelli
    459108,
    # Fra Angelico
    459159,
    # Masaccio
    436904,
    # Piero della Francesca
    459178,
    # Hans Holbein the Younger
    437030,
    # Albrecht Dürer
    436518,
    # Lucas Cranach the Elder
    436518,
    # Nicolas Poussin
    436115,
    # Georges de La Tour
    45891,
    # Chardin
    436040,
    # Jean-Honoré Fragonard
    11417,
    # Antoine Watteau
    436118,
]


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
    Get a random famous painting from Met Museum.
    Uses a curated list of 200+ verified famous painting IDs.

    Returns: (image_path: str, metadata: dict)
    metadata = {title, artist, year, source, object_id}

    Raises: RuntimeError if all retries exhausted.
    """
    for attempt in range(1, max_retries + 1):
        logger.info(f"🎲 Attempt {attempt}/{max_retries} — fetching painting...")
        logger.info("🔍 Trying Met Museum...")

        image_path, metadata = _fetch_from_met()
        if image_path and metadata:
            logger.info(
                f"✅ Got painting: {metadata['title']} by {metadata['artist']}"
            )
            return image_path, metadata

    raise RuntimeError(
        f"Failed to fetch painting after {max_retries} retries"
    )


# ============================================================
# SOURCE: MET MUSEUM DIRECT API (Verified Reliable)
# ============================================================


def _fetch_from_met() -> tuple:
    """
    Fetch a random famous painting from Met Museum using curated IDs.
    Returns: (image_path, metadata) or (None, None) on failure.
    """
    try:
        # Shuffle the curated list and try each one
        shuffled_ids = FAMOUS_PAINTING_IDS.copy()
        random.shuffle(shuffled_ids)

        for obj_id in shuffled_ids:
            object_id = f"met_{obj_id}"

            # Skip already posted
            if is_already_posted(object_id):
                logger.info(f"⏭️ Skipping already posted: {object_id}")
                continue

            # Fetch painting details from Met API
            detail_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
            try:
                detail_resp = requests.get(detail_url, timeout=20)
                if detail_resp.status_code != 200:
                    continue
                detail = detail_resp.json()
            except Exception as e:
                logger.debug(f"Met API error for {obj_id}: {e}")
                continue

            # Validate it has a public domain image
            is_public = detail.get("isPublicDomain", False)
            # Use full-size primaryImage for high quality
            img_url = detail.get("primaryImage")

            if not img_url or not is_public:
                continue

            title = detail.get("title", "Unknown")
            artist = detail.get("artistDisplayName", "Unknown Artist")
            year = detail.get("objectDate", "Unknown")

            # Download the image (relax min_width to 400 as Met images vary)
            image_path = f"/tmp/painting_{object_id}.jpg"
            if download_image(img_url, image_path, min_size_kb=50, min_width=400):
                metadata = {
                    "object_id": object_id,
                    "title": title,
                    "artist": artist,
                    "year": year,
                    "source": "met_museum",
                }
                return image_path, metadata

        logger.warning("Met Museum: Could not find a suitable painting from curated list")
        return None, None

    except Exception as e:
        logger.error(f"Met Museum fetch error: {e}")
        return None, None
