import os
import urllib.request
import math
import struct
import wave
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def download_file(url, dest_path):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if not os.path.exists(dest_path):
        print(f"Downloading {os.path.basename(dest_path)}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"✅ Downloaded {dest_path}")
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
    else:
        print(f"✅ {os.path.basename(dest_path)} already exists.")

def generate_wav(filename, duration, generate_sample_fn, sample_rate=44100):
    wav_path = filename.replace('.mp3', '.wav')
    n_samples = int(duration * sample_rate)
    
    with wave.open(wav_path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        
        for i in range(n_samples):
            t = i / sample_rate
            sample = generate_sample_fn(t, duration)
            # Clip to 16-bit int
            sample = max(-32768, min(32767, int(sample * 32767)))
            f.writeframes(struct.pack('h', sample))
            
    # Convert to mp3 using ffmpeg
    subprocess.run(['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-qscale:a', '2', filename], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(wav_path)
    print(f"✅ Generated {filename}")

# --- Sound Generators ---

import random

def book_open_sound(t, d):
    # Low frequency sweep/rustle
    envelope = math.sin(t / d * math.pi)
    noise = random.uniform(-1, 1) * 0.3
    freq = 50 + 100 * t
    tone = math.sin(2 * math.pi * freq * t) * 0.4
    return (tone + noise) * envelope

def pen_writing_sound(t, d):
    # Modulated high-pass noise for scratching
    envelope = 0.5 + 0.5 * math.sin(2 * math.pi * 8 * t) # writing strokes
    noise = random.uniform(-1, 1)
    # simulate some resonance of paper
    tone = math.sin(2 * math.pi * 1200 * t) * 0.1
    return (noise * 0.5 + tone) * envelope * 0.4

def calculator_click_sound(t, d):
    # Short sharp click
    if t > 0.1: return 0
    envelope = math.exp(-t * 50)
    noise = random.uniform(-1, 1)
    tone = math.sin(2 * math.pi * 2000 * t)
    return (noise * 0.5 + tone * 0.5) * envelope

def stamp_thud_sound(t, d):
    # Low freq punch
    envelope = math.exp(-t * 20)
    freq = max(20, 150 - 500 * t)
    tone = math.sin(2 * math.pi * freq * t)
    return tone * envelope

def book_close_sound(t, d):
    # Quick thud + rustle
    envelope = math.exp(-t * 15)
    noise = random.uniform(-1, 1) * 0.2
    tone = math.sin(2 * math.pi * 80 * t) * 0.8
    return (tone + noise) * envelope

if __name__ == "__main__":
    print("🚀 Setting up assets for Paisa Ka Gyaan...")
    
    # 1. Download Font
    font_url = "https://github.com/google/fonts/raw/main/ofl/kalam/Kalam-Regular.ttf"
    font_dest = os.path.join(BASE_DIR, "assets", "fonts", "handwriting", "Kalam-Regular.ttf")
    download_file(font_url, font_dest)
    
    # 2. Download Background Texture
    bg_url = "https://upload.wikimedia.org/wikipedia/commons/8/8b/Old_paper.jpg"
    bg_dest = os.path.join(BASE_DIR, "assets", "backgrounds", "old_paper_texture.jpg")
    download_file(bg_url, bg_dest)
    
    # 3. Generate Sounds
    sounds_dir = os.path.join(BASE_DIR, "sounds")
    os.makedirs(sounds_dir, exist_ok=True)
    
    generate_wav(os.path.join(sounds_dir, "book_open.mp3"), 1.0, book_open_sound)
    generate_wav(os.path.join(sounds_dir, "pen_writing.mp3"), 4.0, pen_writing_sound)
    generate_wav(os.path.join(sounds_dir, "calculator_click.mp3"), 0.5, calculator_click_sound)
    generate_wav(os.path.join(sounds_dir, "stamp_thud.mp3"), 1.0, stamp_thud_sound)
    generate_wav(os.path.join(sounds_dir, "book_close.mp3"), 1.0, book_close_sound)
    
    print("\n🎉 All assets downloaded and generated successfully!")
