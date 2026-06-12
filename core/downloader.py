"""
Generic Content Downloader — download, validate, and manage images.

Page-specific API logic lives in pages/<page_id>/content_source.py.
This module provides shared download and validation utilities.
"""

import os
import logging
import requests

logger = logging.getLogger("content-automation")


def download_image(url: str, save_path: str, min_size_kb: int = 500, min_width: int = 800) -> bool:
    """
    Download an image from URL.
    Validates: minimum file size and minimum width.

    Args:
        url: Image URL to download
        save_path: Path to save the downloaded image
        min_size_kb: Minimum file size in KB (default 500KB)
        min_width: Minimum image width in pixels (default 800px)

    Returns: True if download succeeded and passes validation.
    """
    try:
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()

        # Check content type
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and "octet" not in content_type:
            logger.debug(f"Not an image: {content_type}")
            return False

        # Save to disk
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Validate file size
        file_size = os.path.getsize(save_path)
        if file_size < min_size_kb * 1024:
            logger.info(
                f"⏭️ Image too small: {file_size // 1024}KB (need {min_size_kb}KB+)"
            )
            os.remove(save_path)
            return False

        # Validate image dimensions
        try:
            from PIL import Image

            with Image.open(save_path) as img:
                width, height = img.size
                if width < min_width:
                    logger.info(
                        f"⏭️ Image too narrow: {width}px (need {min_width}px+)"
                    )
                    os.remove(save_path)
                    return False
        except Exception:
            pass  # PIL check is optional — file size check is primary

        logger.info(f"📥 Downloaded: {save_path} ({file_size // 1024}KB)")
        return True

    except Exception as e:
        logger.debug(f"Download failed for {url}: {e}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False
