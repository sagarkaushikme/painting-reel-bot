# 🎨 Painting Reel Bot

**Fully automated Instagram Reels bot** that creates cinematic art explainer reels from famous paintings.

> Downloads paintings from museum APIs → Gemini AI analyzes dramatic elements → FFmpeg creates zoom-in/zoom-out cinematic reel with Hinglish text → Auto-uploads to Instagram → Runs daily via GitHub Actions (free!)

## 🎬 What It Does

1. **Downloads** a random famous painting from **Rijksmuseum** or **Met Museum** (both free, no API key needed for museums)
2. **Sends** the painting to **Gemini 2.5 Flash Vision** for analysis
3. **Gets back** zoom coordinates + dramatic Hinglish text for each scene
4. **Creates** a cinematic 9:16 vertical reel (zoom-in/zoom-out + text overlay) using **FFmpeg**
5. **Uploads** the reel to **Instagram** via Graph API
6. **Runs daily** at 11:30 AM IST via **GitHub Actions** (completely free, no server needed)

**Niche:** Art history / Famous painting explainer (like `painting_explained` on Instagram)
**Content style:** No voiceover. Only painting + cinematic zoom + dramatic Hinglish text overlay.

---

## 📁 Project Structure

```
painting-reel-bot/
├── .github/workflows/
│   └── daily_post.yml          # GitHub Actions — daily 11:30 AM IST
├── src/
│   ├── __init__.py
│   ├── downloader.py           # Rijksmuseum + Met Museum API
│   ├── analyzer.py             # Gemini Vision — zoom points + text
│   ├── video_maker.py          # FFmpeg — cinematic reel creation
│   ├── uploader.py             # Instagram Graph API + GitHub Releases
│   ├── caption_generator.py    # Captions + hashtags
│   └── utils.py                # Logging, cleanup, validation
├── config/
│   └── painting_blacklist.json # Tracks posted paintings
├── tests/
│   ├── test_downloader.py
│   ├── test_analyzer.py
│   └── test_video_maker.py
├── scripts/
│   └── setup.sh                # One-command local setup
├── main.py                     # Entry point
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **FFmpeg** installed on system
- **Git** + GitHub account

### One-Command Setup

```bash
git clone https://github.com/yourusername/painting-reel-bot
cd painting-reel-bot
bash scripts/setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## 🔑 API Keys Setup

### 1. Gemini API Key (FREE)
1. Visit [aistudio.google.com](https://aistudio.google.com)
2. Click **"Get API Key"** → Create → Copy
3. Free tier: 250 requests/day (we only need 1 per run)
4. Add to `.env`: `GEMINI_API_KEY=your_key_here`

### 2. Instagram Graph API
This requires a few steps:

1. **Switch to Professional Account:**
   - Instagram → Settings → Account → Switch to Professional Account → Creator

2. **Create Facebook App:**
   - Go to [developers.facebook.com](https://developers.facebook.com)
   - Create App → Choose "Business" type
   - Add **Instagram Graph API** product

3. **Link Instagram Account:**
   - Connect your Instagram Business/Creator account to a Facebook Page
   - In the app dashboard, go to Instagram → Settings

4. **Generate Long-Lived Token:**
   ```bash
   # Step 1: Get short-lived token from Graph API Explorer
   # developers.facebook.com/tools/explorer/
   # Select your app, add instagram_basic + instagram_content_publish permissions
   
   # Step 2: Exchange for long-lived token (valid 60 days)
   curl "https://graph.facebook.com/v19.0/oauth/access_token?\
   grant_type=fb_exchange_token&\
   client_id=YOUR_APP_ID&\
   client_secret=YOUR_APP_SECRET&\
   fb_exchange_token=YOUR_SHORT_TOKEN"
   ```

5. Add to `.env`:
   ```
   INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
   INSTAGRAM_USER_ID=your_instagram_user_id
   ```

> ⚠️ **Token Refresh:** Long-lived tokens expire after 60 days. Refresh with:
> ```bash
> curl "https://graph.facebook.com/v19.0/oauth/access_token?\
> grant_type=fb_exchange_token&\
> client_id=YOUR_APP_ID&\
> client_secret=YOUR_APP_SECRET&\
> fb_exchange_token=YOUR_CURRENT_TOKEN"
> ```

### 3. GitHub Token
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Add to `.env`: `GITHUB_TOKEN=your_token`
4. Add to `.env`: `GITHUB_REPO=yourusername/painting-reel-bot`

### 4. Museum APIs (NO SETUP NEEDED! 🎉)
- **Rijksmuseum:** New Data Services API — completely free, no key needed
- **Met Museum:** Open Access API — completely free, no key needed

---

## 🏃 Running Locally

```bash
# Activate venv
source venv/bin/activate

# Run the full pipeline
python main.py
```

Expected output:
```
🚀 Starting Painting Reel Pipeline
✅ All environment variables validated
📥 STEP 1: Downloading painting...
🎨 Got: "The Night Watch" by Rembrandt van Rijn (1642)
🤖 STEP 2: Analyzing painting with Gemini Vision...
🎯 Drama score: 9/10
📖 Story: 34 figures, but only one is looking directly at YOU
🎬 STEP 3: Creating cinematic reel...
  ✅ Segment 1/4 done (3s, zoom=1.0)
  ✅ Segment 2/4 done (5s, zoom=3.0)
  ✅ Segment 3/4 done (5s, zoom=3.5)
  ✅ Segment 4/4 done (4s, zoom=1.0)
🎬 Final reel: /tmp/reel_met_437329.mp4 (43.2MB)
☁️ STEP 4: Hosting video on GitHub Releases...
☁️ Video URL: https://github.com/user/repo/releases/download/...
📝 STEP 5: Generating caption...
📱 STEP 6: Uploading reel to Instagram...
✅ Pipeline complete! Reel posted successfully.
```

---

## ⚙️ GitHub Actions — Automated Daily Posting

### Step 1: Add Secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:
| Secret Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `INSTAGRAM_ACCESS_TOKEN` | Your long-lived token |
| `INSTAGRAM_USER_ID` | Your Instagram user ID |
| `GITHUB_TOKEN` | Your GitHub PAT |

### Step 2: Enable Actions
1. Push your repo to GitHub
2. Go to **Actions** tab
3. Enable the "Daily Painting Reel" workflow
4. Click **"Run workflow"** to test manually
5. Once working, it runs automatically every day at **11:30 AM IST**

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🛠 Technical Details

### Painting Sources
- **Rijksmuseum** — New Linked Open Data API at `data.rijksmuseum.nl`, IIIF images via `iiif.micr.io`
- **Met Museum** — Open Access API, `isHighlight=true` filter for famous works only

### Video Specs
- Resolution: **1080x1920** (9:16 portrait)
- FPS: **25**
- Codec: H.264 (libx264)
- Duration: **~17-20 seconds**
- File size: **~30-50MB**

### FFmpeg Filters Used
- `scale` — Upsample image for smooth zoom
- `zoompan` — Animated zoom to specific coordinates
- `drawtext` — Text overlay with shadow and semi-transparent background

### Duplicate Prevention
`config/painting_blacklist.json` stores posted painting IDs. GitHub Actions auto-commits updates.

### Drama Score Filter
If Gemini rates a painting below 5/10 drama score, the bot automatically picks a different painting.

---

## 📄 License

This project uses public domain artworks from the Rijksmuseum and Metropolitan Museum of Art (CC0 license).
