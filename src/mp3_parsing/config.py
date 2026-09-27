"""
config.py - every setting mp3_parsing needs, loaded from .env, in one
place with nothing else mixed in.

Reading this file top to bottom tells you the whole configurable surface
of the tool: where .env lives, which ffmpeg/ffprobe binaries are used,
where converted files go by default, the default MP3 quality, and the
two timeouts. Nothing here shells out to ffmpeg, touches argparse, or
imports tkinter - every other module in this package imports its
settings from here instead of reading os.environ itself, so there is
exactly one place to look (and to change) when a default needs to move.
"""
import os

from dotenv import load_dotenv

# This file lives at <project_root>/src/mp3_parsing/config.py, so the
# project root - where .env actually lives - is three directories up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# The two command-line tools this project shells out to. Left as bare
# names (not full paths) so whatever ffmpeg/ffprobe the user has on PATH
# is used - see ffmpeg_tools.check_ffmpeg_available() for the "not on
# PATH at all" error message.
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

# Where converted .mp3 files go when nothing overrides it (--output-dir
# on the CLI always wins over this). OUTPUT_DIR in .env can override the
# default "output/" folder under the project root.
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_DIR = os.getenv("OUTPUT_DIR") or DEFAULT_OUTPUT_DIR

# libmp3lame VBR quality scale: "0" (best, ~220-260kbps) to "9" (worst,
# smallest file). --quality on the CLI overrides this.
MP3_QUALITY = os.getenv("MP3_QUALITY", "0")

# ffprobe should return almost instantly; this only guards against a
# truly stuck/unreadable file.
PROBE_TIMEOUT_SECONDS = 30

# Generous ceiling for a single ffmpeg conversion - long enough for a
# multi-hour recording, short enough to eventually give up on a genuinely
# hung ffmpeg process instead of waiting forever.
CONVERT_TIMEOUT_SECONDS = 3600
