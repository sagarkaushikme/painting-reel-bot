"""
Test run — Download painting → Gemini analyze → Create video.
Instagram upload SKIP. Sirf local test.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.downloader import get_random_painting
from src.analyzer import analyze_painting
from src.video_maker import create_reel, add_music_to_reel
from src.caption_generator import generate_caption
from src.utils import setup_logging, resize_image_if_needed, cleanup_temp_files


def test_run():
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("🧪 TEST RUN — No Instagram upload")
    logger.info("=" * 60)

    try:
        # 1. Download painting
        logger.info("")
        logger.info("📥 STEP 1: Downloading painting...")
        image_path, metadata = get_random_painting()
        logger.info(f"🎨 Got: \"{metadata['title']}\"")
        logger.info(f"   Artist: {metadata['artist']}")
        logger.info(f"   Year: {metadata.get('year', 'Unknown')}")
        logger.info(f"   Source: {metadata['source']}")
        logger.info(f"   Image: {image_path}")
        
        # Get image file size
        img_size = os.path.getsize(image_path) / (1024 * 1024)
        logger.info(f"   Size: {img_size:.1f}MB")

        # 1.5 Resize if needed
        image_path = resize_image_if_needed(image_path)

        # 2. Gemini Vision Analysis
        logger.info("")
        logger.info("🤖 STEP 2: Analyzing with Gemini Vision...")
        zoom_data = analyze_painting(image_path, metadata)

        drama_score = zoom_data.get("drama_score", 5)
        hidden_story = zoom_data.get("hidden_story", "")
        sequence = zoom_data.get("zoom_sequence", [])
        mood = zoom_data.get("mood", "mysterious")
        music_intensity = zoom_data.get("music_intensity", "medium")

        logger.info(f"🎯 Drama score: {drama_score}/10")
        logger.info(f"📖 Hidden story: {hidden_story}")
        logger.info(f"🎬 Zoom scenes: {len(sequence)}")
        
        for i, point in enumerate(sequence):
            logger.info(
                f"   Scene {i+1}: zoom={point['zoom_level']}, "
                f"pos=({point['x_percent']:.2f}, {point['y_percent']:.2f}), "
                f"{point['duration_sec']}s — \"{point.get('text', '')}\""
            )

        # 3. Create video
        logger.info("")
        logger.info("🎬 STEP 3: Creating reel with FFmpeg...")
        output_path = f"/tmp/test_reel_{metadata['object_id']}.mp4"
        create_reel(image_path, zoom_data, output_path)

        # 3b. Add music
        music_output = f"/tmp/test_reel_music_{metadata['object_id']}.mp4"
        output_path = add_music_to_reel(
            video_path=output_path,
            mood=mood,
            intensity=music_intensity,
            output_path=music_output
        )

        # Show result
        video_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ TEST COMPLETE!")
        logger.info(f"   📁 Video: {output_path}")
        logger.info(f"   📏 Size: {video_size:.1f}MB")
        logger.info(f"   🎨 Painting: {metadata['title']}")
        logger.info(f"   🎯 Drama: {drama_score}/10")
        logger.info("=" * 60)
        logger.info("")
        logger.info(f"👉 Video dekho: open {output_path}")

        # 4. Generate caption (preview)
        caption = generate_caption(zoom_data, metadata)
        logger.info("")
        logger.info("📝 CAPTION PREVIEW:")
        logger.info("-" * 40)
        print(caption)
        logger.info("-" * 40)

        return output_path

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    test_run()
