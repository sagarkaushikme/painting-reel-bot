"""
Painting Reel Bot — Main Pipeline Entry Point.

Orchestrates the full flow:
1. Validate environment
2. Download a random famous painting
3. Analyze with Gemini Vision (zoom points + Hinglish text)
4. Create cinematic reel with FFmpeg
5. Host video on GitHub Releases
6. Upload reel to Instagram
7. Mark painting as posted (blacklist)
8. Cleanup temp files
"""

import os
import sys
from dotenv import load_dotenv

# Load .env BEFORE importing modules that use env vars
load_dotenv()

from src.downloader import get_random_painting, mark_as_posted
from src.analyzer import analyze_painting
from src.video_maker import create_reel, add_music_to_reel
from src.uploader import host_video_on_github, upload_reel_to_instagram
from src.caption_generator import generate_caption
from src.utils import (
    setup_logging,
    cleanup_temp_files,
    validate_env_vars,
    resize_image_if_needed,
)


def main():
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("🚀 Starting Painting Reel Pipeline")
    logger.info("=" * 60)

    # ---- 0. Validate environment ----
    if not validate_env_vars():
        logger.error("Missing environment variables. Check .env file.")
        sys.exit(1)

    try:
        # ---- 1. Download painting ----
        logger.info("")
        logger.info("📥 STEP 1: Downloading painting...")
        image_path, metadata = get_random_painting()
        logger.info(
            f"🎨 Got: \"{metadata['title']}\" by {metadata['artist']} "
            f"({metadata.get('year', 'Unknown')})"
        )
        logger.info(f"   Source: {metadata['source']}")

        # ---- 1.5. Resize if needed ----
        image_path = resize_image_if_needed(image_path)

        # ---- 2. Gemini Vision Analysis ----
        logger.info("")
        logger.info("🤖 STEP 2: Analyzing painting with Gemini Vision...")
        zoom_data = analyze_painting(image_path, metadata)

        drama_score = zoom_data.get("drama_score", 5)
        hidden_story = zoom_data.get("hidden_story", "")
        num_scenes = len(zoom_data.get("zoom_sequence", []))
        mood = zoom_data.get("mood", "mysterious")
        music_intensity = zoom_data.get("music_intensity", "medium")

        logger.info(f"🎯 Drama score: {drama_score}/10")
        logger.info(f"📖 Story: {hidden_story}")
        logger.info(f"🎬 Scenes: {num_scenes}")
        logger.info(f"🎵 Mood: {mood} (Intensity: {music_intensity})")

        # Drama score filter — skip boring paintings
        if drama_score < 5:
            logger.warning(
                f"⚠️ Drama score too low ({drama_score}/10). "
                "Retrying with a different painting..."
            )
            # Re-download a new painting and re-analyze
            image_path, metadata = get_random_painting()
            image_path = resize_image_if_needed(image_path)
            zoom_data = analyze_painting(image_path, metadata)
            drama_score = zoom_data.get("drama_score", 5)
            mood = zoom_data.get("mood", "mysterious")
            music_intensity = zoom_data.get("music_intensity", "medium")
            logger.info(f"🎯 New drama score: {drama_score}/10")

        # ---- 3. Create video ----
        logger.info("")
        logger.info("🎬 STEP 3: Creating cinematic reel...")
        output_path = f"/tmp/reel_{metadata['object_id']}.mp4"
        create_reel(image_path, zoom_data, output_path)

        # ---- 3b. Add music ----
        music_output = f"/tmp/reel_music_{metadata['object_id']}.mp4"
        output_path = add_music_to_reel(
            video_path=output_path,
            mood=mood,
            intensity=music_intensity,
            output_path=music_output
        )

        # ---- 4. Host video on GitHub Releases ----
        logger.info("")
        logger.info("☁️ STEP 4: Hosting video on GitHub Releases...")
        video_url = host_video_on_github(
            output_path,
            os.getenv("GITHUB_TOKEN"),
            os.getenv("GITHUB_REPO"),
        )
        logger.info(f"☁️ Video URL: {video_url}")

        # ---- 5. Generate caption ----
        logger.info("")
        logger.info("📝 STEP 5: Generating caption...")
        caption = generate_caption(zoom_data, metadata)

        # ---- 6. Upload to Instagram ----
        logger.info("")
        logger.info("📱 STEP 6: Uploading reel to Instagram...")
        upload_reel_to_instagram(
            video_url=video_url,
            caption=caption,
            access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
            ig_user_id=os.getenv("INSTAGRAM_USER_ID"),
        )

        # ---- 7. Mark as posted ----
        mark_as_posted(
            metadata["object_id"],
            metadata["title"],
            metadata["artist"],
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Pipeline complete! Reel posted successfully.")
        logger.info(f"   🎨 {metadata['title']} — {metadata['artist']}")
        logger.info(f"   🎯 Drama: {drama_score}/10")
        logger.info(f"   📖 {hidden_story}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("")
        logger.error(f"❌ Pipeline failed: {e}")
        logger.error("", exc_info=True)
        sys.exit(1)

    finally:
        cleanup_temp_files()


if __name__ == "__main__":
    main()
