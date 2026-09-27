# mp3_parsing

Convert a video (or audio) file into an MP3, keeping the source's original
quality as closely as MP3 allows.

## Project structure

```
mp3_parsing.py              <- entry point: `python mp3_parsing.py ...`
src/mp3_parsing/             <- all the actual implementation, one file per job
    __init__.py               - re-exports the public API; read this first
    config.py                 - .env loading, every tunable constant/default
    ffmpeg_tools.py            - ffprobe checks (available? has audio? duration?)
    progress.py                - pure text formatting for percent/speed/ETA
    converter.py                - the actual ffmpeg conversion (with/without progress)
    gui.py                      - the tkinter desktop window
    cli.py                      - argparse command-line entry point + main()
tests/test_mp3_parsing.py   <- tests against the src/mp3_parsing/ package
```

The root `mp3_parsing.py` script is intentionally tiny - it just points
Python at `src/` and calls `cli.main()` - so `python mp3_parsing.py ...`
keeps working exactly as before. Every file under `src/mp3_parsing/` has a
single, narrow job described in its own docstring, so picking one to read
- whether you're new to the codebase or not - tells you everything that
file is responsible for without needing the rest open at the same time.

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your PATH
  (`ffmpeg` and `ffprobe` both need to run from a terminal). On Windows,
  download a build, unzip it, and add its `bin/` folder to your PATH.
- `pip install -r requirements.txt` (just `python-dotenv`)

## Usage

Both the GUI and the CLI show a live progress bar while a file converts -
percent complete, ffmpeg's own encode speed (e.g. "3.2x"), elapsed time,
and an estimated time remaining (ETA) - using ffmpeg's machine-readable
`-progress pipe:1` output. ETA is derived from how much source audio is
left divided by the current speed, so it settles down after the first
couple of updates; it shows as `--:--` until ffmpeg has reported a usable
speed (or if the input's duration couldn't be read).

### GUI (no command line needed)

Run with no arguments at all:

```
python mp3_parsing.py
```

A small window (tkinter) opens - click "Choose files..." to pick one or
more video/audio files (.mp4/.wav filter, switchable to "All files"), then
click "Convert". A progress bar and a label like
`clip.mp4: 48.3% (3.2x speed) - elapsed 0:12, ETA 0:08` update live for the
file currently converting. If a file fails, the process stops immediately
at that file (it does not silently skip it and continue with the rest).

### Command line

```
python mp3_parsing.py <input_file> [--output-dir DIR] [--quality N]
```

While converting, the CLI prints a live-updating progress line, for
example:

```
[##############----------------]  48.3% (3.2x) elapsed 0:12 ETA 0:08
```

- `<input_file>` - path to a video or audio file. `.mp4` and `.wav` are the
  two formats this is tested against, but anything FFmpeg can read works
  the same way (the file's actual audio stream is what gets checked, not
  its extension).
- `--output-dir` - where to write the `.mp3` (default: `OUTPUT_DIR` from
  `.env`, or `output/` under this project if `.env` doesn't set it).
- `--quality` - FFmpeg's `libmp3lame` VBR quality scale, `0` (best,
  roughly 220-260kbps) to `9` (worst/smallest file). Default: `MP3_QUALITY`
  from `.env`, or `0`.

Example:

```
python mp3_parsing.py "recording.mp4"
# -> output/recording.mp3

python mp3_parsing.py "recording.wav" --output-dir converted --quality 4
# -> converted/recording.mp3, smaller/lower-quality than the default
```

The output file is named after the input (same basename, `.mp3`
extension) and overwrites an existing file with the same name.

## Configuration (.env)

Copy `.env.example` to `.env` to override the defaults - both settings are
optional:

| Key | Default | Meaning |
|---|---|---|
| `OUTPUT_DIR` | `output` | Folder new `.mp3` files are written to. |
| `MP3_QUALITY` | `0` | FFmpeg `libmp3lame` VBR quality, `0` (best) - `9` (worst). |

Sample rate and channel count are never forced - a mono recording stays
mono and a stereo one stays stereo; FFmpeg only resamples on its own if
the source's sample rate isn't one MP3 can represent.

## Tests

```
python -m unittest tests.test_mp3_parsing -v
```

Needs real `ffmpeg`/`ffprobe` on PATH - the whole suite skips cleanly
(not a failure) if they're missing. Test clips are generated on the fly
with FFmpeg's `lavfi` virtual input, so there are no fixture files to
commit or download.

## History

This project was previously a full video-to-transcript pipeline (Whisper
transcription, speaker diarization, LLM-based correction and topic
segmentation). That code and its docs (`CODE_REVIEW.md`, old `README.md`)
were moved into `to_delete/` when the project was repurposed into this
single-purpose MP3 converter - nothing was deleted outright except the
large local test video fixtures, which are recoverable from source video
files if ever needed again.
