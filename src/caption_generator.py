"""
Caption Generator — Creates engaging Instagram captions with hashtags.
"""

import re
import logging

logger = logging.getLogger("painting-reel-bot")


def generate_caption(zoom_data: dict, metadata: dict) -> str:
    """
    Generate an Instagram caption for the painting reel.

    Format:
    💀 {hidden_story}

    #hashtags...
    """
    artist = metadata.get("artist", "Unknown Artist")
    source = metadata.get("source", "")

    # Extract hidden story from analysis metadata
    hidden_story = zoom_data.get(
        "hidden_story", "Ek aisi painting jisne art history badal di."
    )

    # 1-line story with an emoji
    lines = [
        f"💀 {hidden_story}",
        "",
        _generate_hashtags(artist, source)
    ]

    caption = "\n".join(lines)

    # Instagram caption limit is 2200 chars
    if len(caption) > 2200:
        caption = caption[:2190] + "..."

    logger.info(f"📝 Caption generated ({len(caption)} chars)")
    return caption


def _generate_hashtags(artist: str, source: str) -> str:
    """Generate a curated hashtag string."""
    # Core hashtags (always included)
    tags = [
        "#painting",
        "#art",
        "#arthistory",
        "#viral",
        "#facts",
        "#history",
        "#paintings",
        "#artwork",
        "#masterpiece",
        "#museum",
        "#artlovers",
        "#fineart",
        "#classicart",
        "#artexplained",
        "#hindiart",
        "#indianartlover",
        "#artfacts",
        "#paintingexplained",
        "#famouspainting",
        "#artreels",
    ]

    # Artist-specific hashtag
    if artist and artist != "Unknown Artist":
        # Convert artist name to hashtag format
        artist_tag = re.sub(r"[^a-zA-Z0-9]", "", artist.lower())
        if artist_tag:
            tags.append(f"#{artist_tag}")

    # Source-specific
    if source == "rijksmuseum":
        tags.extend(["#rijksmuseum", "#dutchmasters", "#dutchart"])
    elif source == "met_museum":
        tags.extend(["#metmuseum", "#themet", "#nyc"])

    # Niche engagement tags
    tags.extend([
        "#reels",
        "#explore",
        "#trending",
    ])

    # Instagram allows max 30 hashtags — trim if needed
    tags = tags[:30]

    return " ".join(tags)
