"""
ffmpeg_tools.py - short-lived ffprobe/ffmpeg checks: is ffmpeg installed,
does this file actually have an audio track, how long is it.

Everything here finishes in a few seconds (or fails fast with a clear
RuntimeError) - none of it runs the actual, possibly long, MP3 conversion.
That live, streaming ffmpeg process is converter.py's job; this module
only ever answers yes/no/how-long questions before or around it.
"""
import json
import shutil
import subprocess

from .config import FFMPEG_BIN, FFPROBE_BIN, PROBE_TIMEOUT_SECONDS


def check_ffmpeg_available() -> None:
    """Fail fast with a clear message if ffmpeg/ffprobe aren't on PATH."""
    for binary in (FFMPEG_BIN, FFPROBE_BIN):
        if shutil.which(binary) is None:
            raise RuntimeError(
                f"Could not find '{binary}' on PATH. Please install FFmpeg and try again."
            )


def has_audio_track(input_path: str) -> bool:
    """
    Ask ffprobe whether the file actually has an audio stream to extract -
    catches a video with no sound, a corrupted file, or something ffmpeg
    can't read at all, with one clear error instead of a confusing ffmpeg
    failure further down.
    """
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        input_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True,
                                text=True, timeout=PROBE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"ffprobe did not finish within {PROBE_TIMEOUT_SECONDS}s - is the file readable?")
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe could not read '{input_path}':\n{result.stderr}")

    info = json.loads(result.stdout)
    return any(s.get("codec_type") == "audio" for s in info.get("streams", []))


def get_duration_seconds(input_path: str) -> float:
    """
    Ask ffprobe for the input's duration in seconds, used only to turn
    ffmpeg's raw "out_time_ms so far" progress output into a percentage.
    Returns 0.0 (instead of raising) on any failure - the progress bar
    then just can't show a percent/ETA and falls back to speed-only
    display, which is a cosmetic degradation, not a reason to fail the
    conversion.
    """
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        input_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True,
                                text=True, timeout=PROBE_TIMEOUT_SECONDS)
        if result.returncode != 0:
            return 0.0
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0.0))
    except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError):
        return 0.0
