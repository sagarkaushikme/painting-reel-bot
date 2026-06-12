import os
import yaml
from core import analyzer, video_maker
from core.utils import setup_logging
from pages.paisa_ka_gyaan import content_source as pkg_cs
from pages.paisa_ka_gyaan.prompts import VISION_PROMPT
from dotenv import load_dotenv

load_dotenv()
logger = setup_logging()

with open('pages/paisa_ka_gyaan/config.yaml') as f:
    config = yaml.safe_load(f)

# 1. Get content
print("Generating topic...")
_, metadata = pkg_cs.get_content(config)

# 2. Analyze
print("Analyzing topic with Gemini...")
analysis = analyzer.analyze_content(None, VISION_PROMPT, metadata)

# 3. Create video
output_path = "/Users/sagarkaushik/.gemini/antigravity-ide/brain/90a50d73-f060-466f-9533-8f77c6a2d14c/paisa_test.mp4"
print(f"Creating video at {output_path}...")
video_maker.create_diary_reel(analysis, config, output_path)

# 4. Add music
print("Adding music...")
final_video = "/Users/sagarkaushik/.gemini/antigravity-ide/brain/90a50d73-f060-466f-9533-8f77c6a2d14c/paisa_final_test.mp4"
video_maker.add_music_to_reel(output_path, analysis.get("mood", "mysterious"), analysis.get("music_intensity", "low"), final_video)

print(f"✅ Done! Final video saved to {final_video}")
