"""
Content Automation System — Multi-Page Pipeline Entry Point.

Orchestrates the full flow for ANY page:
1. Load page config + modules dynamically
2. Get content (page-specific source)
3. Analyze with Gemini (generic core, page-specific prompt)
4. Create video (painting zoom or diary mode)
5. Add music
6. Generate caption
7. Upload to Instagram + YouTube
8. Mark as posted (blacklist)
9. Cleanup temp files

Usage:
    python main.py painting_explained
    python main.py paisa_ka_gyaan
"""

import sys
import os
import yaml
import importlib
from dotenv import load_dotenv

# Load .env BEFORE importing modules that use env vars
load_dotenv()

from core import analyzer, video_maker, uploader
from core.utils import setup_logging, cleanup_temp_files, resize_image_if_needed
from core.caption_generator import generate_caption


def run_page(page_id: str):
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info(f"🚀 Starting pipeline for page: {page_id}")
    logger.info("=" * 60)

    # Load page config
    config_path = f"pages/{page_id}/config.yaml"
    if not os.path.exists(config_path):
        logger.error(f"❌ Page config not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Load page-specific modules dynamically
    prompts_module = importlib.import_module(f"pages.{page_id}.prompts")
    content_source = importlib.import_module(f"pages.{page_id}.content_source")

    try:
        # ---- 1. Get content (image + metadata) — page-specific logic ----
        logger.info("")
        logger.info("📥 STEP 1: Getting content...")
        image_path, metadata = content_source.get_content(config)

        if image_path:
            logger.info(
                f"🎨 Got: \"{metadata.get('title', 'Unknown')}\" "
                f"by {metadata.get('artist', 'Unknown')}"
            )
            # Resize if needed (only for image-based pages)
            image_path = resize_image_if_needed(image_path)
        else:
            logger.info(f"📖 Generated content: {metadata.get('title', 'Unknown')}")

        # ---- 2. Analyze with Gemini — generic core, page-specific prompt ----
        logger.info("")
        logger.info("🤖 STEP 2: Analyzing content with Gemini...")
        analysis = analyzer.analyze_content(
            image_path,
            prompts_module.VISION_PROMPT,
            metadata
        )

        drama_score = analysis.get("drama_score", 5)
        hidden_story = analysis.get("hidden_story", "")
        mood = analysis.get("mood", "mysterious")
        music_intensity = analysis.get(
            "music_intensity",
            config.get("music_intensity_default", "medium")
        )

        logger.info(f"🎯 Drama score: {drama_score}/10")
        logger.info(f"📖 Story: {hidden_story}")
        logger.info(f"🎵 Mood: {mood} (Intensity: {music_intensity})")

        # Drama score filter — retry with new content if too low
        if drama_score < 5:
            logger.warning(
                f"⚠️ Drama score too low ({drama_score}/10). "
                "Retrying with new content..."
            )
            image_path, metadata = content_source.get_content(config)
            if image_path:
                image_path = resize_image_if_needed(image_path)
            analysis = analyzer.analyze_content(
                image_path, prompts_module.VISION_PROMPT, metadata
            )
            drama_score = analysis.get("drama_score", 5)
            mood = analysis.get("mood", "mysterious")
            music_intensity = analysis.get(
                "music_intensity",
                config.get("music_intensity_default", "medium")
            )
            logger.info(f"🎯 New drama score: {drama_score}/10")

        # ---- 3. Create video ----
        logger.info("")
        logger.info("🎬 STEP 3: Creating video...")

        visual_style = config.get("visual_style", "painting_zoom")

        if visual_style == "diary_ledger":
            # Diary mode — create from scratch using background + text
            output_path = f"/tmp/reel_{page_id}.mp4"
            video_maker.create_diary_reel(analysis, config, output_path)
        else:
            # Painting zoom mode — zoom on downloaded image
            object_id = metadata.get("object_id", page_id)
            output_path = f"/tmp/reel_{object_id}.mp4"
            video_maker.create_reel(image_path, analysis, output_path)

        # ---- 4. Add music ----
        logger.info("")
        logger.info("🎧 STEP 4: Adding music...")
        final_video = f"/tmp/final_{page_id}.mp4"
        output_path = video_maker.add_music_to_reel(
            video_path=output_path,
            mood=mood,
            intensity=music_intensity,
            output_path=final_video
        )

        # ---- 5. Generate caption ----
        logger.info("")
        logger.info("📝 STEP 5: Generating caption...")
        caption = generate_caption(analysis, metadata, config)

        # ---- 6. Upload ----
        logger.info("")
        logger.info("☁️ STEP 6: Uploading...")

        # Host video on GitHub
        github_token = os.getenv("GITHUB_TOKEN")
        github_repo = os.getenv("GITHUB_REPOSITORY") or os.getenv("GITHUB_REPO")

        if github_token and github_repo:
            video_url = uploader.host_video_on_github(
                output_path, github_token, github_repo
            )
            logger.info(f"☁️ Video URL: {video_url}")

            # Upload to Instagram
            ig_token = os.getenv(config["instagram"]["access_token_env"])
            ig_user_id = os.getenv(config["instagram"]["user_id_env"])

            if ig_token and ig_user_id:
                uploader.upload_reel_to_instagram(
                    video_url=video_url,
                    caption=caption,
                    access_token=ig_token,
                    ig_user_id=ig_user_id,
                )
            else:
                logger.warning("⚠️ Instagram credentials not set, skipping IG upload")
        else:
            logger.warning("⚠️ GitHub credentials not set, skipping upload")

        # Upload to YouTube Shorts if enabled
        if config.get("youtube", {}).get("enabled"):
            uploader.upload_to_youtube_shorts(output_path, caption, config)

        # ---- 7. Mark as posted ----
        content_source.mark_as_posted(metadata, page_id)

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ {page_id} pipeline complete!")
        logger.info(f"   📖 {metadata.get('title', 'Unknown')}")
        logger.info(f"   🎯 Drama: {drama_score}/10")
        logger.info(f"   📖 {hidden_story}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("")
        logger.error(f"❌ {page_id} pipeline failed: {e}")
        logger.error("", exc_info=True)
        raise

    finally:
        cleanup_temp_files()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <page_id>")
        print("Example: python main.py painting_explained")
        print("         python main.py paisa_ka_gyaan")
        sys.exit(1)

    page_id = sys.argv[1]
    run_page(page_id)
