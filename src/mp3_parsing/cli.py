"""
cli.py - the command-line entry point.

`python mp3_parsing.py <file> [--output-dir DIR] [--quality N]` converts
one file with a live one-line progress bar. `python mp3_parsing.py` with
no arguments at all opens the GUI (gui.launch_gui()) instead of failing
on argparse's required positional input_file.
"""
import argparse
import sys

from .converter import convert_to_mp3
from .gui import launch_gui
from .progress import format_progress_bar


def main() -> None:
    if len(sys.argv) == 1:
        launch_gui()
        return

    parser = argparse.ArgumentParser(
        description="Convert a video/audio file to MP3.")
    parser.add_argument(
        "input_file", help="Path to the source file (.mp4, .wav, or anything ffmpeg can read).")
    parser.add_argument("--output-dir", default=None,
                        help="Where to write the .mp3 (default: OUTPUT_DIR from .env, or 'output/').")
    parser.add_argument("--quality", default=None,
                        help="libmp3lame VBR quality, 0 (best) - 9 (worst). Default: MP3_QUALITY from .env, or 0.")
    args = parser.parse_args()

    def _cli_progress(percent: float, speed: str, elapsed: float, eta) -> None:
        sys.stdout.write(format_progress_bar(percent, speed, elapsed, eta))
        sys.stdout.flush()

    try:
        output_path = convert_to_mp3(
            args.input_file, output_dir=args.output_dir, quality=args.quality,
            progress_callback=_cli_progress)
    except RuntimeError as exc:
        print()
        sys.exit(f"Error: {exc}")

    print(f"\nDone: {output_path}")
