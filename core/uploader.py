"""
Instagram + YouTube Uploader — Upload reels via Graph API + host video on GitHub Releases.

Flow:
1. Upload video to GitHub Releases → get public URL
2. Create Instagram media container with video URL
3. Poll for processing completion
4. Publish the reel
"""

import os
import time
import logging
import requests
from datetime import datetime

logger = logging.getLogger("content-automation")


# ============================================================
# GITHUB RELEASES — VIDEO HOSTING (free public URL)
# ============================================================


def host_video_on_github(
    video_path: str, github_token: str, repo: str
) -> str:
    """
    Upload video to GitHub Releases as an asset.
    Creates a release tagged with today's date, uploads the MP4.

    Returns: public browser_download_url for the asset.
    Raises: RuntimeError on failure.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    tag = datetime.now().strftime("reel-%Y-%m-%d-%H%M%S")
    release_name = f"Content Reel — {datetime.now().strftime('%Y-%m-%d')}"

    # Step 1: Create a release
    logger.info(f"☁️ Creating GitHub release: {tag}...")

    create_url = f"https://api.github.com/repos/{repo}/releases"
    release_data = {
        "tag_name": tag,
        "name": release_name,
        "body": "Auto-generated content reel",
        "draft": False,
        "prerelease": False,
    }

    resp = requests.post(
        create_url, json=release_data, headers=headers, timeout=30
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"GitHub release creation failed ({resp.status_code}): {resp.text}"
        )

    release = resp.json()
    upload_url_template = release["upload_url"]
    # Template looks like: https://uploads.github.com/.../assets{?name,label}
    upload_url = upload_url_template.split("{")[0]

    # Step 2: Upload video as release asset
    logger.info(f"☁️ Uploading video ({os.path.getsize(video_path) // (1024*1024)}MB)...")

    filename = os.path.basename(video_path)
    upload_headers = {
        "Authorization": f"token {github_token}",
        "Content-Type": "video/mp4",
    }

    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            f"{upload_url}?name={filename}",
            headers=upload_headers,
            data=f,
            timeout=300,  # 5 min timeout for large uploads
        )

    if upload_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"GitHub asset upload failed ({upload_resp.status_code}): "
            f"{upload_resp.text[:300]}"
        )

    asset = upload_resp.json()
    download_url = asset["browser_download_url"]

    logger.info(f"✅ Video hosted: {download_url}")
    return download_url


# ============================================================
# INSTAGRAM GRAPH API — REEL UPLOAD
# ============================================================


def upload_reel_to_instagram(
    video_url: str,
    caption: str,
    access_token: str,
    ig_user_id: str,
) -> bool:
    """
    Upload a reel to Instagram via Graph API.

    2-step process:
    1. Create media container → get container_id
    2. Wait for processing → publish

    Returns: True on success.
    Raises: RuntimeError on failure.
    """
    api_version = "v19.0"
    base_url = f"https://graph.facebook.com/{api_version}"

    # ---- Step 1: Create media container ----
    logger.info("📱 Creating Instagram media container...")

    container_resp = requests.post(
        f"{base_url}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": access_token,
        },
        timeout=60,
    )

    if container_resp.status_code != 200:
        raise RuntimeError(
            f"Instagram container creation failed "
            f"({container_resp.status_code}): {container_resp.text}"
        )

    container_id = container_resp.json().get("id")
    if not container_id:
        raise RuntimeError(
            f"No container ID in response: {container_resp.text}"
        )

    logger.info(f"📱 Container created: {container_id}")

    # ---- Step 2: Wait for video processing ----
    logger.info("⏳ Waiting for Instagram to process video...")

    max_attempts = 30  # 30 * 10 sec = 5 min max wait
    for attempt in range(1, max_attempts + 1):
        status_resp = requests.get(
            f"{base_url}/{container_id}",
            params={
                "fields": "status_code",
                "access_token": access_token,
            },
            timeout=30,
        )

        if status_resp.status_code != 200:
            logger.warning(
                f"Status check failed: {status_resp.text}"
            )
            time.sleep(10)
            continue

        status = status_resp.json().get("status_code")
        logger.info(f"  Processing status: {status} (attempt {attempt}/{max_attempts})")

        if status == "FINISHED":
            break
        elif status == "ERROR":
            error_info = status_resp.json()
            raise RuntimeError(
                f"Instagram video processing failed: {error_info}"
            )

        time.sleep(10)
    else:
        raise RuntimeError(
            "Instagram video processing timed out after 5 minutes"
        )

    # ---- Step 3: Publish the reel ----
    logger.info("📱 Publishing reel...")

    publish_resp = requests.post(
        f"{base_url}/{ig_user_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=60,
    )

    if publish_resp.status_code == 200:
        media_id = publish_resp.json().get("id", "unknown")
        logger.info(f"✅ Reel published! Media ID: {media_id}")
        return True
    else:
        raise RuntimeError(
            f"Instagram publish failed ({publish_resp.status_code}): "
            f"{publish_resp.text}"
        )


# ============================================================
# YOUTUBE SHORTS UPLOAD (placeholder — requires OAuth2 setup)
# ============================================================


def upload_to_youtube_shorts(video_path: str, caption: str, config: dict) -> bool:
    """
    Upload video to YouTube Shorts.

    NOTE: This requires YouTube Data API v3 OAuth2 setup.
    For now, this is a placeholder that logs a warning.
    Full implementation needs google-auth + google-api-python-client.
    """
    logger.warning(
        "⚠️ YouTube Shorts upload not yet implemented. "
        "Requires OAuth2 setup with YouTube Data API v3."
    )
    return False
