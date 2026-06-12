"""
Caption Generator — Creates engaging Instagram captions with hashtags.

Handles different page types with page-specific formatting.
"""

import re
import logging

logger = logging.getLogger("content-automation")


def generate_caption(analysis: dict, metadata: dict, config: dict) -> str:
    """
    Generate an Instagram caption for the reel.

    Uses config to determine page-specific caption format.
    Hashtags come from config.yaml instead of being hardcoded.
    """
    page_id = config.get("page_id", "unknown")
    hashtags = " ".join(config.get("caption_hashtags", []))

    hidden_story = analysis.get(
        "hidden_story", "Ek aisi kahani jo aapne pehle nahi suni."
    )

    if page_id == "paisa_ka_gyaan":
        caption = f"""📖 {metadata.get('title', 'Finance Fact')}

{hidden_story}

{hashtags}"""

    elif page_id == "painting_explained":
        artist = metadata.get("artist", "Unknown Artist")
        source = metadata.get("source", "Museum Collection")
        title = metadata.get("title", "Unknown Painting")

        caption = f"""🎨 {title} — {artist}

{hidden_story}

📍 {source}
📌 Save karo — roz ek nayi story

{hashtags}"""

        # Add artist-specific hashtag
        if artist and artist != "Unknown Artist":
            artist_tag = re.sub(r"[^a-zA-Z0-9]", "", artist.lower())
            if artist_tag:
                caption += f" #{artist_tag}"

        # Add source-specific hashtags
        if source == "rijksmuseum":
            caption += " #rijksmuseum #dutchmasters #dutchart"
        elif source == "met_museum":
            caption += " #metmuseum #themet #nyc"

    else:
        # Generic fallback for any new page type
        caption = f"""💡 {metadata.get('title', 'Interesting Fact')}

{hidden_story}

{hashtags}"""

    # Instagram caption limit is 2200 chars
    if len(caption) > 2200:
        caption = caption[:2190] + "..."

    logger.info(f"📝 Caption generated ({len(caption)} chars)")
    return caption
