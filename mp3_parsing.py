#!/usr/bin/env python3
"""
mp3_parsing.py - entry point script. Run this: `python mp3_parsing.py ...`

Every bit of actual implementation lives in src/mp3_parsing/ (config.py,
ffmpeg_tools.py, progress.py, converter.py, gui.py, cli.py) - this file's
only job is to put that folder on sys.path and hand off to its main().
See src/mp3_parsing/__init__.py for a one-paragraph map of what each file
in there does.

Kept as a standalone root-level script (rather than requiring
`python -m src.mp3_parsing` or similar) so the command people already
run/pin in shortcuts, docs, and muscle memory - `python mp3_parsing.py` -
keeps working unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from mp3_parsing.cli import main

if __name__ == "__main__":
    main()
