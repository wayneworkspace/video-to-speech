"""
mp3_parsing - convert a video or audio file into an MP3, keeping the
source's original quality as closely as MP3 allows.

Input: any file ffmpeg can read that has an audio track. .mp4 and .wav
are the two formats this is written and tested against, but nothing here
checks the file extension - ffprobe reads the file's real streams, so
anything else ffmpeg understands (.mov, .mkv, .m4a, ...) works the same
way.

This package is split by responsibility so each file stays small enough
for anyone - intern, fresher, or senior - to read start to finish and
know exactly what it's for:

    config.py         - .env loading and every tunable constant/default
    ffmpeg_tools.py    - short ffprobe checks: available? has audio? duration?
    progress.py        - pure text formatting for percent/speed/elapsed/ETA
    converter.py        - the actual ffmpeg conversion (with/without progress)
    gui.py              - the tkinter desktop window (tkinter imported lazily)
    cli.py              - argparse command-line entry point + main()

Read them in that order for the full picture: config first (what can be
configured), then ffmpeg_tools and progress (small, dependency-free
helpers), then converter (how they're used to actually run ffmpeg), then
gui/cli (the two front doors people actually run).

This __init__.py re-exports the names other code - including the test
suite - actually needs, so `import mp3_parsing` behaves the same as it
did when this was a single file; callers don't need to know which
submodule something now lives in.
"""
from .config import (
    FFMPEG_BIN,
    FFPROBE_BIN,
    OUTPUT_DIR,
    MP3_QUALITY,
    PROJECT_ROOT,
)
from .ffmpeg_tools import check_ffmpeg_available, has_audio_track, get_duration_seconds
from .converter import convert_to_mp3
from .gui import launch_gui
from .cli import main

__all__ = [
    "FFMPEG_BIN",
    "FFPROBE_BIN",
    "OUTPUT_DIR",
    "MP3_QUALITY",
    "PROJECT_ROOT",
    "check_ffmpeg_available",
    "has_audio_track",
    "get_duration_seconds",
    "convert_to_mp3",
    "launch_gui",
    "main",
]
