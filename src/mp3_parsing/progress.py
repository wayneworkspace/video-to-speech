"""
progress.py - pure formatting helpers for the live progress display:
turning numbers ffmpeg/the converter produce into text a person reads.

Nothing in this file runs a subprocess or touches a file on disk - every
function takes plain numbers/strings in and returns a plain string (or
None) out, so each one can be understood and unit-tested in isolation
from the actual ffmpeg process (that live process is converter.py's job;
deciding *where* this text is shown - a terminal line vs. a GUI label -
is cli.py's and gui.py's job).
"""


def format_duration(seconds) -> str:
    """
    Format a duration in seconds as "M:SS" (or "H:MM:SS" once it reaches
    an hour). None - meaning "not known yet", e.g. the ETA before ffmpeg
    has reported a usable speed - renders as "--:--".
    """
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_speed(speed: str):
    """
    Parse ffmpeg's own "3.2x" progress speed string into a float
    multiplier. Returns None when it isn't a usable positive number yet
    (ffmpeg reports "N/A" for the first report or two, before it has
    enough samples to compute a rate) - the caller then can't derive an
    ETA from it for that update.
    """
    text = speed.strip().rstrip("x")
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def format_progress_bar(percent: float, speed: str, elapsed: float, eta, width: int = 30) -> str:
    """
    Build one CLI progress line, e.g.:
        [##############----------------]  48.3% (3.2x) elapsed 0:12 ETA 0:08
    Starts with "\\r" (carriage return, no newline) so printing it
    repeatedly overwrites the same terminal line instead of scrolling.
    """
    filled = int(width * percent / 100)
    bar = "#" * filled + "-" * (width - filled)
    return (
        f"\r[{bar}] {percent:5.1f}% ({speed}) "
        f"elapsed {format_duration(elapsed)} ETA {format_duration(eta)}"
    )
