"""
converter.py - the actual MP3 conversion: convert_to_mp3() is the one
function everything else in this project (CLI, GUI, tests) calls to turn
a video/audio file into an MP3.

Two code paths live here, on purpose:
  - progress_callback=None (the default): a single blocking
    subprocess.run() call, byte-for-byte the same as this project's very
    first version. Every existing test calls convert_to_mp3() this way,
    so this path must never change behavior.
  - progress_callback given: a streaming subprocess.Popen() call that
    parses ffmpeg's own "-progress pipe:1" output to report live percent/
    speed/elapsed/ETA back to the caller. This is what the CLI and GUI
    use so the person watching sees a progress bar instead of a frozen
    terminal/window.
"""
import os
import subprocess
import threading
import time

from .config import FFMPEG_BIN, CONVERT_TIMEOUT_SECONDS, OUTPUT_DIR, MP3_QUALITY
from .ffmpeg_tools import check_ffmpeg_available, has_audio_track, get_duration_seconds
from .progress import parse_speed


def _run_ffmpeg_with_progress(cmd: list, total_seconds: float, progress_callback) -> str:
    """
    Run ffmpeg with "-progress pipe:1" already appended to `cmd`, parsing
    its machine-readable key=value lines from stdout to compute a percent
    (out_time_ms / total_seconds), read ffmpeg's own self-reported encode
    speed (e.g. "3.2x"), track elapsed wall-clock time since this call
    started, and estimate time remaining (ETA) from the audio still left
    to encode divided by the current speed multiplier - calling
    progress_callback(percent, speed, elapsed, eta) as each update
    arrives (elapsed/eta in seconds; eta is None when it can't be
    estimated yet, e.g. before ffmpeg reports a usable speed or when the
    input's duration is unknown). Returns collected stderr (ffmpeg's
    actual human-readable errors, since "-loglevel error" keeps that
    quiet unless something is actually wrong) so the caller can report
    failures.

    stdout and stderr are drained concurrently (stderr on a background
    thread) to avoid a classic subprocess deadlock: with both piped, if
    only one is read from the main thread, the other's OS pipe buffer can
    fill up and block ffmpeg forever once it writes enough to it.

    ffmpeg emits one key=value line per field per report cycle, always
    ending the cycle with a "progress=continue" (or "progress=end") line
    - "speed=" arrives *after* "out_time_ms=" within the same cycle, so
    the callback is fired on the "progress=" line (once both are known
    for that cycle) rather than on "out_time_ms=" directly; firing on
    out_time_ms would report this cycle's percent next to the *previous*
    cycle's speed.
    """
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )

    stderr_lines: list = []

    def _drain_stderr():
        for line in process.stderr:
            stderr_lines.append(line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    speed = "0x"
    out_time_ms = None
    start_time = time.monotonic()
    try:
        for line in process.stdout:
            if time.monotonic() - start_time > CONVERT_TIMEOUT_SECONDS:
                process.kill()
                raise RuntimeError(
                    f"MP3 conversion did not finish within {CONVERT_TIMEOUT_SECONDS}s.")

            line = line.strip()
            key, sep, value = line.partition("=")
            if not sep:
                continue

            if key == "speed":
                speed = value.strip() or speed
            elif key == "out_time_ms":
                try:
                    out_time_ms = int(value)
                except ValueError:
                    out_time_ms = None
            elif key == "progress":
                elapsed = time.monotonic() - start_time
                if value == "end":
                    progress_callback(100.0, speed, elapsed, 0.0)
                elif out_time_ms is not None:
                    out_seconds = out_time_ms / 1_000_000
                    percent = min(100.0, out_seconds / total_seconds * 100) if total_seconds > 0 else 0.0
                    eta = None
                    speed_value = parse_speed(speed)
                    if total_seconds > 0 and speed_value:
                        remaining_source_seconds = max(0.0, total_seconds - out_seconds)
                        eta = remaining_source_seconds / speed_value
                    progress_callback(percent, speed, elapsed, eta)
    finally:
        process.wait(timeout=10)
        stderr_thread.join(timeout=10)

    if process.returncode != 0:
        raise RuntimeError(f"MP3 conversion failed:\n{''.join(stderr_lines)[-2000:]}")

    return "".join(stderr_lines)


def convert_to_mp3(input_path: str, output_dir: str = None, quality=None, progress_callback=None) -> str:
    """
    Convert `input_path` to an MP3 in `output_dir` (default: OUTPUT_DIR
    from .env). Returns the path to the MP3 file it wrote. Raises
    RuntimeError with a clear message for every failure mode (missing
    file, missing ffmpeg, no audio track, ffmpeg itself failing/timing out)
    rather than letting a raw traceback surface.

    Sample rate and channel count are never forced (no -ar/-ac), so a
    mono recording stays mono and a stereo one stays stereo, matching the
    source as closely as MP3 allows - ffmpeg only resamples on its own if
    the source rate is not one MP3 can represent. Quality is libmp3lame
    VBR (-q:a): "0" (best, ~220-260kbps) to "9" (worst/smallest file).

    progress_callback, if given, is called as progress_callback(percent,
    speed, elapsed, eta) while ffmpeg runs (percent: 0-100 float; speed:
    ffmpeg's own string like "3.2x"; elapsed: seconds since conversion
    started; eta: estimated seconds remaining, or None when it can't be
    estimated yet). Leaving it as None (the default) keeps the exact
    original subprocess.run-based code path with no progress plumbing at
    all, so every existing caller (including the test suite) is unaffected.
    """
    if not os.path.isfile(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    check_ffmpeg_available()

    if not has_audio_track(input_path):
        raise RuntimeError(f"'{input_path}' has no audio track to extract.")

    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    basename = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{basename}.mp3")

    quality = MP3_QUALITY if quality is None else quality

    if progress_callback is None:
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_path,
            "-vn",
            "-codec:a", "libmp3lame",
            "-q:a", str(quality),
            output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True,
                                    text=True, timeout=CONVERT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"MP3 conversion did not finish within {CONVERT_TIMEOUT_SECONDS}s.")
        if result.returncode != 0:
            raise RuntimeError(f"MP3 conversion failed:\n{result.stderr[-2000:]}")
        return output_path

    total_seconds = get_duration_seconds(input_path)
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-vn",
        "-codec:a", "libmp3lame",
        "-q:a", str(quality),
        "-progress", "pipe:1",
        "-nostats", "-loglevel", "error",
        output_path,
    ]
    _run_ffmpeg_with_progress(cmd, total_seconds, progress_callback)
    return output_path
