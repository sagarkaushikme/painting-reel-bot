"""
FFmpeg Video Maker — Creates cinematic 9:16 Instagram Reels.

Uses FFmpeg zoompan filter for smooth zoom-in/zoom-out effects,
and drawtext filter for Hinglish text overlays with shadow.
"""

import os
import subprocess
import logging
import shutil
import textwrap

logger = logging.getLogger("painting-reel-bot")


# ============================================================
# MAIN REEL CREATOR
# ============================================================


def create_reel(image_path: str, zoom_data: dict, output_path: str) -> str:
    """
    Creates Instagram Reel from painting + zoom data.

    Output specs:
    - Resolution: 1080x1920 (9:16 portrait)
    - FPS: 25
    - Format: MP4 (H.264 video, no audio)
    - Duration: sum of all segment durations (~17-20 sec)

    Returns: path to final MP4 file.
    Raises: RuntimeError if FFmpeg fails.
    """
    # Verify FFmpeg is installed
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg not found! Install it:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt-get install ffmpeg"
        )

    sequence = zoom_data.get("zoom_sequence", [])
    if not sequence:
        raise ValueError("Empty zoom sequence — nothing to render")

    logger.info(
        f"🎬 Creating reel with {len(sequence)} segments..."
    )

    segments = []

    for i, point in enumerate(sequence):
        segment_path = f"/tmp/segment_{i}.mp4"
        _create_segment(image_path, point, segment_path, i)
        segments.append(segment_path)
        logger.info(
            f"  ✅ Segment {i + 1}/{len(sequence)} done "
            f"({point['duration_sec']}s, zoom={point['zoom_level']})"
        )

    # Concatenate all segments into final reel
    _concat_segments(segments, output_path)

    # Cleanup individual segments
    _cleanup_segments(segments)

    # Report final file info
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"🎬 Final reel: {output_path} ({size_mb:.1f}MB)")
    else:
        raise RuntimeError(f"Output file not created: {output_path}")

    return output_path


# ============================================================
# MUSIC ADDER
# ============================================================


def add_music_to_reel(
    video_path: str,
    mood: str, 
    intensity: str,
    output_path: str
) -> str:
    from src.music_selector import select_music
    
    track_path, peak_start, volume = select_music(mood, intensity)
    
    if not track_path:
        # Music nahi mili → silently skip, video as-is return karo
        logger.warning("⚠️ No music track found, skipping music addition.")
        shutil.copy(video_path, output_path)
        return output_path
    
    # Video duration nikalo
    import json
    probe = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", video_path
    ], capture_output=True, text=True)
    
    try:
        duration = float(json.loads(probe.stdout)["format"]["duration"])
    except Exception as e:
        logger.error(f"❌ Failed to probe video duration: {e}")
        shutil.copy(video_path, output_path)
        return output_path
    
    logger.info(f"🎧 Mixing background music ({mood}, Vol: {volume})...")
    
    # FFmpeg — video + music mix karo
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(peak_start),
        "-i", track_path,
        "-filter_complex",
        f"[1:a]volume={volume},atrim=0:{duration},apad[music]",
        "-map", "0:v",
        "-map", "[music]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]
    
    result = subprocess.run(
        cmd, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        logger.error(f"❌ Failed to mix music: {result.stderr[-500:]}")
        # Music fail → original video return karo
        shutil.copy(video_path, output_path)
    else:
        logger.info(f"✅ Music mixed successfully → {output_path}")
    
    return output_path


# ============================================================
# INDIVIDUAL SEGMENT CREATION
# ============================================================


def _create_segment(
    image_path: str, point: dict, output_path: str, segment_index: int
):
    """
    Create a single zoom segment with text overlay.

    Uses FFmpeg filters:
    - scale: upsample image for smooth zoom
    - zoompan: animated zoom to specific coordinates
    - drawtext: Hinglish text with shadow and semi-transparent background
    """
    x_pct = float(point.get("x_percent", 0.5))
    y_pct = float(point.get("y_percent", 0.5))
    zoom = float(point.get("zoom_level", 1.0))
    duration = int(point.get("duration_sec", 4))
    text = str(point.get("text", ""))
    text_pos = point.get("text_position", "bottom")
    fps = 25
    frames = duration * fps

    # ---- Text styling & sizing ----
    text_len = len(text)
    if text_len > 22:
        fontsize = 75
    elif text_len > 15:
        fontsize = 85
    else:
        fontsize = 100

    # ---- Text wrapping & file writing ----
    # Wrap text to 18 characters per line
    wrapped_text = ""
    text_file_path = f"/tmp/seg_text_{segment_index}.txt"
    if text.strip():
        wrapped_text = "\n".join(textwrap.wrap(text.lower(), width=18))
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(wrapped_text)

    # ---- Text timing ----
    # 0.2s delay to start, stays until the end to maximize reading time
    start_time = 0.2
    end_time = duration
    enable_expr = f"between(t,{start_time},{end_time})"

    # ---- Text position ----
    if text_pos == "top":
        text_y = "250"  # Not extreme top
    else:
        text_y = "h-text_h-350"  # Moved up to avoid Instagram UI overlap

    # ---- Zoom expression ----
    # zoompan z parameter: starts at 1.0 and smoothly increases to target
    if zoom <= 1.05:
        # No zoom — keep at 1.0
        zoom_expr = "1.0"
    else:
        # Smooth ease-in zoom: gradually zoom from 1.0 to target level
        # Use 80% of frames to reach target, then hold
        zoom_increment = (zoom - 1.0) / (frames * 0.8)
        zoom_expr = f"min(zoom+{zoom_increment:.6f},{zoom})"

    # ---- Pan expressions ----
    # zoompan x/y: pixel position of the top-left corner of the visible area
    # Formula: position = fraction * (image_width - visible_width)
    #   visible_width = image_width / zoom
    #   so: x = fraction * (iw - iw/zoom)
    x_expr = f"({x_pct}*(iw-iw/zoom))"
    y_expr = f"({y_pct}*(ih-ih/zoom))"

    # ---- Find a font file ----
    font_path = _find_font()
    font_spec = f"fontfile='{font_path}':" if font_path else ""

    # ---- Build the video filter chain ----
    vf_parts = [
        # Upsample for smooth zoom (zoompan works better on larger images)
        "scale=5000:-1",
        # Animated zoom + pan
        (
            f"zoompan="
            f"z='{zoom_expr}':"
            f"x='{x_expr}':"
            f"y='{y_expr}':"
            f"d={frames}:"
            f"s=1080x1920:"
            f"fps={fps}"
        ),
    ]

    # Add text overlay only if text is non-empty
    if wrapped_text.strip():
        vf_parts.append(
            f"drawtext="
            f"{font_spec}"
            f"textfile='{text_file_path}':"
            f"enable='{enable_expr}':"
            f"fontcolor=white:"
            f"fontsize={fontsize}:"
            f"x=(w-text_w)/2:"
            f"y={text_y}:"
            f"borderw=4:"
            f"bordercolor=black:"
            f"shadowx=0:"
            f"shadowy=0:"
            f"line_spacing=20"
        )

    vf = ",".join(vf_parts)

    # ---- Build FFmpeg command ----
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-loop", "1",  # Loop the single image
        "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-pix_fmt", "yuv420p",  # Compatibility
        "-c:v", "libx264",
        "-preset", "medium",  # Better quality encoding
        "-crf", "18",  # Higher bitrate/quality (was 23)
        output_path,
    ]

    logger.debug(f"FFmpeg cmd: {' '.join(cmd[:6])}...")

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
        raise RuntimeError(
            f"FFmpeg segment {segment_index} failed:\n{error_msg}"
        )


# ============================================================
# SEGMENT CONCATENATION
# ============================================================


def _concat_segments(segments: list, output_path: str):
    """
    Concatenate multiple MP4 segments into one final video.
    Uses FFmpeg concat demuxer for lossless joining.
    """
    concat_file = "/tmp/concat_list.txt"

    with open(concat_file, "w") as f:
        for seg in segments:
            # Use absolute path for safety
            abs_path = os.path.abspath(seg)
            f.write(f"file '{abs_path}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",  # No re-encoding — fast and lossless
        output_path,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60
    )

    if result.returncode != 0:
        error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
        raise RuntimeError(f"FFmpeg concat failed:\n{error_msg}")

    # Cleanup concat file
    try:
        os.remove(concat_file)
    except OSError:
        pass

    logger.info(f"✅ Segments concatenated → {output_path}")


# ============================================================
# HELPERS
# ============================================================


def _cleanup_segments(segments: list):
    """Remove individual segment files after concatenation."""
    for seg in segments:
        try:
            os.remove(seg)
        except OSError:
            pass


def _escape_ffmpeg_text(text: str) -> str:
    """
    Escape special characters for FFmpeg drawtext filter.
    FFmpeg drawtext uses : , [ ] ' as special chars.
    """
    if not text:
        return ""

    # Order matters — escape backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")  # Shell-safe single quote escape
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace(";", "\\;")
    text = text.replace("%", "%%")  # FFmpeg uses % for timestamps

    return text


def _find_font() -> str:
    """
    Find or download Roboto Bold font to support lowercase.
    """
    import urllib.request
    
    font_dir = "/tmp/fonts"
    font_path = os.path.join(font_dir, "Roboto-Bold.ttf")
    
    # Download Roboto Bold directly from Google Fonts GitHub
    if not os.path.exists(font_path):
        os.makedirs(font_dir, exist_ok=True)
        try:
            logger.info("📥 Downloading Roboto Bold font...")
            # Direct link to the TTF file
            url = "https://raw.githubusercontent.com/googlefonts/roboto-2/main/src/hinted/Roboto-Bold.ttf"
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            logger.warning(f"⚠️ Failed to download font: {e}")
    
    if os.path.exists(font_path):
        return font_path

    # Fallbacks if download failed
    font_candidates = [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]

    for f_path in font_candidates:
        if os.path.exists(f_path):
            return f_path

    logger.warning("⚠️ No font file found — FFmpeg will use default")
    return ""
