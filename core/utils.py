"""
Utility functions — logging, cleanup, validation, image processing.

Generic utilities shared across all pages.
"""

import os
import sys
import glob
import logging
from PIL import Image


def setup_logging() -> logging.Logger:
    """
    Structured logging with timestamps.
    Returns configured logger for the pipeline.
    """
    logger = logging.getLogger("content-automation")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-import
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def cleanup_temp_files():
    """
    Delete all temporary pipeline files from /tmp/.
    Patterns: painting_*.jpg, segment_*.mp4, reel_*.mp4, diary_seg_*.mp4, final_*.mp4
    """
    patterns = [
        "/tmp/painting_*",
        "/tmp/segment_*",
        "/tmp/reel_*",
        "/tmp/diary_seg_*",
        "/tmp/final_*",
        "/tmp/concat_list.txt",
        "/tmp/seg_text_*",
    ]
    removed = 0
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                os.remove(filepath)
                removed += 1
            except OSError:
                pass

    logger = logging.getLogger("content-automation")
    logger.info(f"🧹 Cleaned up {removed} temp files")


def validate_env_vars(required_vars: list) -> bool:
    """
    Check that all required environment variables are set before running.
    Takes a list of env var names to validate.
    Returns True if all present, False otherwise.
    """
    logger = logging.getLogger("content-automation")
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            missing.append(var)

    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        return False

    logger.info("✅ All environment variables validated")
    return True


def resize_image_if_needed(image_path: str, min_width: int = 1500) -> str:
    """
    If image is too small, FFmpeg zoom won't look good.
    Resize up to min_width while maintaining aspect ratio.
    Returns path to (possibly resized) image.
    """
    logger = logging.getLogger("content-automation")

    try:
        img = Image.open(image_path)
        width, height = img.size

        if width >= min_width:
            logger.info(f"📐 Image size OK: {width}x{height}")
            return image_path

        # Calculate new dimensions maintaining aspect ratio
        ratio = min_width / width
        new_width = min_width
        new_height = int(height * ratio)

        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Save resized image (overwrite original temp file)
        resized_path = image_path.replace(".jpg", "_resized.jpg")
        img_resized.save(resized_path, "JPEG", quality=95)
        img.close()
        img_resized.close()

        logger.info(
            f"📐 Image resized: {width}x{height} → {new_width}x{new_height}"
        )
        return resized_path

    except Exception as e:
        logger.warning(f"⚠️ Image resize failed: {e}, using original")
        return image_path


def get_image_size_bytes(filepath: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def get_image_dimensions(filepath: str) -> tuple:
    """Get image width, height. Returns (0, 0) on error."""
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)
