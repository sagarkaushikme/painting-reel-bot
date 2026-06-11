import os
import shutil
import logging
from src.music_selector import select_music
from src.video_maker import add_music_to_reel

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("painting-reel-bot")

MOODS = [
    "dark_horror",
    "mysterious",
    "melancholic",
    "epic",
    "devotional",
    "romantic"
]

def create_sample_video():
    """Create a quick 5 second sample video using FFmpeg to test audio mixing."""
    sample_path = "/tmp/sample_silent_video.mp4"
    if os.path.exists(sample_path):
        return sample_path
        
    logger.info("🎬 Creating a 5-second sample silent video...")
    os.system(f"ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=5 -c:v libx264 -pix_fmt yuv420p {sample_path} -hide_banner -loglevel error")
    return sample_path

def test_all_moods():
    sample_video = create_sample_video()
    
    for mood in MOODS:
        logger.info(f"--- Testing Mood: {mood} ---")
        output_path = f"/tmp/test_{mood}.mp4"
        
        try:
            result_path = add_music_to_reel(
                video_path=sample_video,
                mood=mood,
                intensity="medium",
                output_path=output_path
            )
            
            if os.path.exists(result_path):
                logger.info(f"✅ Created: {result_path}")
            else:
                logger.error(f"❌ Failed to create: {result_path}")
        except Exception as e:
            logger.error(f"❌ Error testing mood {mood}: {e}")

if __name__ == "__main__":
    test_all_moods()
