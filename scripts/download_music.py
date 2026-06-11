import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("music-downloader")

MOODS = [
    "dark_horror",
    "mysterious",
    "melancholic",
    "epic",
    "devotional",
    "romantic"
]

# Using archive.org and other stable open-source URLs to avoid scraper blocking
TRACKS = {
    "dark_horror": [
        {
            "url": "https://archive.org/download/ToccataAndFugueInDMinor_437/toccata_and_fugue_in_d_minor.mp3",
            "filename": "toccata_peak_10s.mp3"
        },
        {
            "url": "https://archive.org/download/MozartRequiem_59/01RequiemAeternam.mp3",
            "filename": "requiem_dark_peak_5s.mp3"
        }
    ],
    "mysterious": [
        {
            "url": "https://archive.org/download/InTheHallOfTheMountainKing_940/InTheHallOfTheMountainKing.mp3",
            "filename": "hall_mountain_king_peak_45s.mp3"
        },
        {
            "url": "https://archive.org/download/bolero_201912/Bolero.mp3",
            "filename": "bolero_mystery_peak_10s.mp3"
        }
    ],
    "melancholic": [
        {
            "url": "https://archive.org/download/MoonlightSonata_755/Beethoven-MoonlightSonata.mp3",
            "filename": "moonlight_sonata_peak_0s.mp3"
        },
        {
            "url": "https://archive.org/download/MozartRequiem_59/08LacrimosaDiesIlla.mp3",
            "filename": "lacrimosa_peak_8s.mp3"
        }
    ],
    "epic": [
        {
            "url": "https://archive.org/download/RideOfTheValkyries_816/RideOfTheValkyries.mp3",
            "filename": "valkyries_epic_peak_15s.mp3"
        },
        {
            "url": "https://archive.org/download/HolstThePlanets_990/01MarsTheBringerOfWar.mp3",
            "filename": "mars_war_peak_0s.mp3"
        }
    ],
    "devotional": [
        {
            "url": "https://archive.org/download/AveMaria_896/AveMaria.mp3",
            "filename": "ave_maria_peak_0s.mp3"
        },
        {
            "url": "https://archive.org/download/gregorian-chant-mass/gregorian_chant.mp3",
            "filename": "gregorian_chant_peak_0s.mp3"
        }
    ],
    "romantic": [
        {
            "url": "https://archive.org/download/clair-de-lune_202008/Clair%20de%20Lune.mp3",
            "filename": "clair_de_lune_peak_0s.mp3"
        },
        {
            "url": "https://archive.org/download/chopin_nocturne_op9_no2/Chopin%20Nocturne%20Op.%209%20No.%202.mp3",
            "filename": "chopin_nocturne_peak_0s.mp3"
        }
    ]
}

def setup_folders():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music")
    os.makedirs(base_dir, exist_ok=True)
    
    for mood in MOODS:
        mood_dir = os.path.join(base_dir, mood)
        os.makedirs(mood_dir, exist_ok=True)
        
    return base_dir

def download_tracks(base_dir):
    for mood, tracks in TRACKS.items():
        mood_dir = os.path.join(base_dir, mood)
        for track in tracks:
            url = track["url"]
            filename = track["filename"]
            file_path = os.path.join(mood_dir, filename)
            
            if os.path.exists(file_path):
                logger.info(f"⏭️ Skipping {filename} (already exists)")
                continue
                
            try:
                logger.info(f"📥 Downloading {filename} into {mood}/...")
                urllib.request.urlretrieve(url, file_path)
                logger.info(f"✅ Success: {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to download {filename}: {e}")
                # We won't crash, so it continues to try others
                
if __name__ == "__main__":
    logger.info("🎵 Starting Music Download Script...")
    base_dir = setup_folders()
    download_tracks(base_dir)
    logger.info("🎵 Finished setting up music library!")
