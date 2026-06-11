import os
import random
import logging

logger = logging.getLogger("painting-reel-bot")

MOOD_FOLDER_MAP = {
    "dark_horror": "music/dark_horror/",
    "mysterious": "music/mysterious/",
    "melancholic": "music/melancholic/",
    "epic": "music/epic/",
    "devotional": "music/devotional/",
    "romantic": "music/romantic/"
}

INTENSITY_VOLUME = {
    "low": 15.00,
    "medium": 25.00,
    "high": 40.00
}

def select_music(mood: str, intensity: str):
    """
    Returns: (track_path, peak_start_seconds, volume)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_rel = MOOD_FOLDER_MAP.get(mood, "music/mysterious/")
    folder = os.path.join(base_dir, folder_rel)
    
    if not os.path.exists(folder):
        logger.warning(f"⚠️ Music folder not found: {folder}")
        return None, 0, 0.20
        
    tracks = [f for f in os.listdir(folder) if f.endswith('.mp3')]
    
    if not tracks:
        logger.warning(f"⚠️ No MP3 tracks found in {folder}")
        return None, 0, 0.20
    
    chosen = random.choice(tracks)
    track_path = os.path.join(folder, chosen)
    
    # Filename se peak time nikalo
    # "toccata_peak_10s.mp3" → 10
    try:
        peak_sec = int(chosen.split("_peak_")[1].replace("s.mp3", ""))
    except Exception:
        peak_sec = 0
    
    volume = INTENSITY_VOLUME.get(intensity, 0.22)
    
    logger.info(f"🎵 Selected Music: {chosen} (Mood: {mood}, Peak: {peak_sec}s, Vol: {volume})")
    
    return track_path, peak_sec, volume
